import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import statistics
import re
from pathlib import Path
import openai

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.agent_config import sql_analysis_agent, AgentResponse
from agents import Runner, Agent
from utils.context_detector import ExecutionContext
from database_tool import run_sql_query

@dataclass
class TestResult:
    """Results for a single test execution"""
    test_name: str
    variant_name: str
    run_number: int
    produced_screenshots: bool = False
    screenshot_count: int = 0
    avg_screenshot_relevance: float = 0.0
    avg_feature_relevance: float = 0.0
    found_feature_ids: List[str] = field(default_factory=list)
    correct_features_found: int = 0
    total_correct_features: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None
    developer_note: Optional[str] = None
    # New fields for retrieval rate calculation
    total_available_screenshots: int = 0
    retrieval_rate: float = 0.0
    screenshots_retrieved_for_correct_features: int = 0
    # New fields for ChatGPT scoring
    chatgpt_relevance_score: Optional[float] = None
    chatgpt_rationale: Optional[str] = None
    chatgpt_scoring_error: Optional[str] = None

@dataclass
class VariantResults:
    """Aggregated results for a variant across multiple runs"""
    variant_name: str
    runs: List[TestResult] = field(default_factory=list)
    
    def aggregate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics across all runs"""
        if not self.runs:
            return {}
        
        successful_runs = [r for r in self.runs if r.error is None]
        if not successful_runs:
            return {"all_runs_failed": True}
        
        # Helper function to safely calculate mean
        def safe_mean(values):
            if not values:
                return 0.0
            return statistics.mean(values)
        
        return {
            "total_runs": len(self.runs),
            "successful_runs": len(successful_runs),
            "error_rate": (len(self.runs) - len(successful_runs)) / len(self.runs),
            "screenshot_production_rate": sum(1 for r in successful_runs if r.produced_screenshots) / len(successful_runs) if successful_runs else 0,
            "avg_screenshot_count": safe_mean([r.screenshot_count for r in successful_runs]),
            "avg_screenshot_relevance": safe_mean([r.avg_screenshot_relevance for r in successful_runs if r.avg_screenshot_relevance > 0]),
            "avg_feature_relevance": safe_mean([r.avg_feature_relevance for r in successful_runs if r.avg_feature_relevance > 0]),
            "avg_correct_features_found": safe_mean([r.correct_features_found for r in successful_runs]),
            "avg_execution_time": safe_mean([r.execution_time for r in successful_runs]),
            # New retrieval rate metrics
            "avg_total_available_screenshots": safe_mean([r.total_available_screenshots for r in successful_runs if r.total_available_screenshots > 0]),
            "avg_retrieval_rate": safe_mean([r.retrieval_rate for r in successful_runs if r.retrieval_rate > 0]),
            "avg_screenshots_retrieved_for_correct_features": safe_mean([r.screenshots_retrieved_for_correct_features for r in successful_runs]),
            # ChatGPT scoring metrics
            "chatgpt_scoring_success_rate": sum(1 for r in successful_runs if r.chatgpt_relevance_score is not None) / len(successful_runs) if successful_runs else 0,
            "avg_chatgpt_relevance_score": safe_mean([r.chatgpt_relevance_score for r in successful_runs if r.chatgpt_relevance_score is not None]),
        }

class EvalFramework:
    def __init__(self, config_path: str):
        """Initialize the evaluation framework with a config file"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.results: Dict[str, Dict[str, VariantResults]] = {}
        
    def load_system_prompt_variant(self, variant_path: str) -> str:
        """Load a system prompt variant from file"""
        with open(variant_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def extract_metrics_from_response(self, response: str, test_config: Dict) -> Dict[str, Any]:
        """Extract basic metrics from the agent's response (keeping only screenshot detection and relevance scores)"""
        metrics = {
            "produced_screenshots": False,
            "screenshot_count": 0,
            "avg_screenshot_relevance": 0.0,
            "avg_feature_relevance": 0.0,
            "found_feature_ids": [],  # Kept for fallback compatibility
        }
        
        # Enhanced screenshot detection - look for content that indicates screenshots were shown
        screenshot_indicators = [
            "screenshot",
            "showing",
            "displaying",
            "images",
            "visual",
            "examples",
            "interface",
            "tutorial"
        ]
        
        screenshot_detected = any(indicator in response.lower() for indicator in screenshot_indicators)
        
        if screenshot_detected:
            metrics["produced_screenshots"] = True
            
            # Try to extract screenshot count from response content
            count_patterns = [
                r'(\d+)\s*screenshot',
                r'showing\s*(\d+)',
                r'(\d+)\s*examples',
                r'(\d+)\s*images'
            ]
            
            for pattern in count_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    metrics["screenshot_count"] = int(matches[0])
                    break
        
        # Enhanced relevance score extraction from response content
        relevance_patterns = [
            r'relevance[_\s]*score[:\s]*([0-9.]+)',
            r'relevance[:\s]*([0-9.]+)',
            r'score[:\s]*([0-9.]+)',
            r'similarity[:\s]*([0-9.]+)'
        ]
        
        all_scores = []
        for pattern in relevance_patterns:
            scores = re.findall(pattern, response, re.IGNORECASE)
            if scores:
                all_scores.extend([float(score) for score in scores])
        
        if all_scores:
            # Split scores between features and screenshots (heuristic)
            mid = len(all_scores) // 2
            if len(all_scores) > 1:
                metrics["avg_feature_relevance"] = statistics.mean(all_scores[:mid]) if all_scores[:mid] else 0
                metrics["avg_screenshot_relevance"] = statistics.mean(all_scores[mid:]) if all_scores[mid:] else 0
            else:
                # If only one score, assume it's feature relevance
                metrics["avg_feature_relevance"] = all_scores[0]
        
        # FALLBACK ONLY: Feature ID extraction from text (used only when database lookup fails)
        feature_id_patterns = [
            r'feature[_\s]*id[:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'id[:\s]*([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
        ]
        
        found_ids = set()
        for pattern in feature_id_patterns:
            ids = re.findall(pattern, response, re.IGNORECASE)
            found_ids.update(ids)
        
        metrics["found_feature_ids"] = list(found_ids)
        
        return metrics
    
    async def score_with_chatgpt(self, conversation_history: List[Dict[str, str]], user_question: str) -> Dict[str, Any]:
        """
        Use ChatGPT to score how relevant the assistant's answer is to the user's question
        
        Args:
            conversation_history: List of conversation messages with 'role' and 'content' keys
            user_question: The original user question to evaluate relevance against
            
        Returns:
            Dict with 'score', 'rationale', and optional 'error' keys
        """
        try:
            from openai import AsyncOpenAI
            
            # Set up OpenAI client - assumes API key is in environment
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {"error": "OpenAI API key not found in environment variables"}
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Format the conversation for ChatGPT evaluation
            conversation_text = ""
            for msg in conversation_history:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                conversation_text += f"{role}: {content}\n\n"
            
            # Create the evaluation prompt
            evaluation_prompt = f"""
You are an expert evaluator of AI assistant responses. Your task is to score how relevant and helpful an assistant's answer is to the user's question.

Original User Question: "{user_question}"

Conversation:
{conversation_text}

Please evaluate the assistant's response based on:
1. How directly it addresses the user's question
2. How helpful and informative the response is
3. How well it provides actionable information or guidance
4. Overall relevance to the user's intent

Provide your evaluation as a JSON object with exactly this format:
{{
    "score": <number between 0.0 and 1.0>,
    "rationale": "<detailed explanation of your scoring reasoning>"
}}

Score Guidelines:
- 1.0: Perfect relevance, completely addresses the question with helpful information
- 0.8-0.9: Highly relevant, mostly addresses the question with good information
- 0.6-0.7: Moderately relevant, partially addresses the question
- 0.4-0.5: Somewhat relevant but missing key information
- 0.2-0.3: Minimally relevant, tangentially relates to the question
- 0.0-0.1: Not relevant, doesn't address the question

Respond ONLY with the JSON object, no other text.
"""

            # Make the API call with JSON mode enforced
            response = await client.chat.completions.create(
                model="gpt-4o",  # Use gpt-4o which supports JSON mode
                messages=[
                    {"role": "system", "content": "You are a helpful evaluation assistant that responds only with valid JSON."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=500
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            result = json.loads(response_text)
            
            # Validate the response format
            if "score" not in result or "rationale" not in result:
                return {"error": f"Invalid response format from ChatGPT: {response_text}"}
            
            # Validate score is a number between 0 and 1
            try:
                score = float(result["score"])
                if not (0.0 <= score <= 1.0):
                    return {"error": f"Score {score} is not between 0.0 and 1.0"}
                result["score"] = score
            except (ValueError, TypeError):
                return {"error": f"Invalid score format: {result['score']}"}
            
            return result
            
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse ChatGPT response as JSON: {e}"}
        except Exception as e:
            return {"error": f"ChatGPT scoring failed: {e}"}
    
    async def run_single_test(self, test_config: Dict, variant_name: str, variant_prompt: str, run_number: int) -> TestResult:
        """Run a single test with a specific variant"""
        test_name = test_config["name"]
        start_time = datetime.now()
        
        result = TestResult(
            test_name=test_name,
            variant_name=variant_name,
            run_number=run_number,
            total_correct_features=len(test_config.get("correct_features", []))
        )
        
        # Track tasks for proper cleanup
        created_tasks = []
        
        try:
            # Import the agent tools here to avoid import issues
            from utils.agent_tools import run_sql_query_tool, retrieve_screenshots_for_display_tool, semantic_search_tool
            
            # Clear session state before test
            ExecutionContext._mock_session_state.clear()
            
            # Create a new agent with the variant prompt instead of copying
            modified_agent = Agent(
                name="SQL Analysis Agent (Eval Variant)",
                instructions=variant_prompt,
                tools=[semantic_search_tool, run_sql_query_tool, retrieve_screenshots_for_display_tool],
                output_type=AgentResponse
            )
            
            # Run the conversation
            conversation_history = []
            full_response = ""
            
            for step in test_config["steps"]:
                # Build input with conversation history
                if conversation_history:
                    history_context = "Previous conversation:\n"
                    for msg in conversation_history:
                        history_context += f"{msg['role']}: {msg['content']}\n"
                    history_context += f"\nCurrent question: {step}"
                    agent_input = history_context
                else:
                    agent_input = step
                
                # Run the agent with proper task management
                try:
                    # Run the agent
                    agent_result = await Runner.run(modified_agent, agent_input)
                    
                    if isinstance(agent_result.final_output, AgentResponse):
                        response = agent_result.final_output.user_reponse
                        result.developer_note = agent_result.final_output.developer_note
                    else:
                        response = str(agent_result.final_output)
                    
                    full_response += f"\n{response}"
                    
                    # Update conversation history
                    conversation_history.append({"role": "user", "content": step})
                    conversation_history.append({"role": "assistant", "content": response})
                    
                except Exception as step_error:
                    print(f"[EVAL] Error in conversation step '{step}': {step_error}")
                    response = f"Error: {step_error}"
                    full_response += f"\nError: {step_error}"
                    break
            
            result.raw_response = full_response
            
            # Extract metrics from the response (for screenshot indicators and relevance scores)
            metrics = self.extract_metrics_from_response(full_response, test_config)
            
            # Check if screenshots were actually retrieved by examining session state
            screenshots_data = ExecutionContext.get_session_state_value("screenshots_to_display", None)
            screenshot_ids_found = []
            
            if screenshots_data:
                result.produced_screenshots = True
                # Count actual screenshots from the data structure
                total_screenshots = 0
                if isinstance(screenshots_data, list):
                    # screenshots_data is a list of groups, each group contains screenshot_data
                    for group in screenshots_data:
                        if isinstance(group, dict):
                            # Extract screenshot IDs and count screenshots
                            if "screenshot_data" in group:
                                for screenshot in group["screenshot_data"]:
                                    if isinstance(screenshot, dict) and "screenshot_id" in screenshot:
                                        screenshot_ids_found.append(screenshot["screenshot_id"])
                                total_screenshots += len(group["screenshot_data"])
                            # Alternative: count image_paths if screenshot_data not available
                            elif "image_paths" in group:
                                total_screenshots += len(group["image_paths"])
                    result.screenshot_count = total_screenshots
                else:
                    result.screenshot_count = len(screenshots_data) if screenshots_data else 0
                
                print(f"[EVAL] Successfully retrieved {result.screenshot_count} screenshots across {len(screenshots_data)} groups")
                print(f"[EVAL] Found {len(screenshot_ids_found)} screenshot IDs for feature lookup")
            else:
                # Fall back to text pattern detection
                result.produced_screenshots = metrics["produced_screenshots"]
                result.screenshot_count = metrics["screenshot_count"]
                print(f"[EVAL] No screenshots in session state, using text patterns: {result.produced_screenshots}")
            
            result.avg_screenshot_relevance = metrics["avg_screenshot_relevance"]
            result.avg_feature_relevance = metrics["avg_feature_relevance"]
            
            # **NEW: Deterministic feature ID extraction from screenshot tool results**
            found_feature_ids = set()
            
            if screenshots_data:
                # Extract feature information directly from the screenshot tool results
                try:
                    # The screenshots_data contains groups with feature information
                    for group in screenshots_data:
                        if isinstance(group, dict):
                            group_title = group.get("group_title", "")
                            screenshot_data = group.get("screenshot_data", [])
                            
                            # Log the group information
                            print(f"[EVAL] Screenshot group: '{group_title}' with {len(screenshot_data)} screenshots")
                            
                            # If group title is not "Untagged Screenshots", it represents a feature
                            if group_title and group_title != "Untagged Screenshots" and group_title != "Unknown Feature":
                                # Check if we have feature mapping from semantic search tool results in session state
                                semantic_results = ExecutionContext.get_session_state_value("last_semantic_search_results", None)
                                if semantic_results:
                                    # Look for feature matches in semantic search results
                                    features_from_search = semantic_results.get("features", [])
                                    for search_result in features_from_search:
                                        result_name = search_result.get("name", "").lower()
                                        group_name = group_title.lower()
                                        
                                        # Enhanced matching: exact, partial, and keyword matching
                                        match_found = False
                                        
                                        # 1. Exact match (case-insensitive)
                                        if result_name == group_name:
                                            match_found = True
                                        
                                        # 2. Partial matching (either direction)
                                        elif result_name in group_name or group_name in result_name:
                                            match_found = True
                                        
                                        # 3. Keyword matching for events and special features
                                        elif any(keyword in result_name for keyword in group_name.split()):
                                            match_found = True
                                        elif any(keyword in group_name for keyword in result_name.split()):
                                            match_found = True
                                        
                                        if match_found:
                                            feature_id = search_result.get("feature_id")
                                            if feature_id:
                                                found_feature_ids.add(str(feature_id))
                                                print(f"[EVAL] Matched feature via semantic search: '{group_title}' -> Feature ID {feature_id} ('{search_result.get('name')}')")
                                
                                # Enhanced direct feature name mapping for known patterns
                                feature_name_mapping = {
                                    # Mini-games
                                    "mini-games": "17",
                                    "minigames": "17", 
                                    "mini games": "17",
                                    
                                    # Events (common patterns)
                                    "sheep rescue": "1006",  # Example event mapping
                                    "sheep rescue event": "1006",
                                    "arcade fever": "1021",
                                    "arcade fever event": "1021", 
                                    "seasonal event": "1024",
                                    
                                    # Core features
                                    "mine": "37",
                                    "mining": "37",
                                    "coins": "8",
                                    "farming": "1",
                                    "train": "4",
                                    "train station": "4"
                                }
                                
                                # Try direct mapping with flexible matching
                                group_lower = group_title.lower()
                                for name_pattern, feature_id in feature_name_mapping.items():
                                    # Check for exact match or if pattern is contained in group name
                                    if name_pattern == group_lower or name_pattern in group_lower:
                                        found_feature_ids.add(feature_id)
                                        print(f"[EVAL] Matched feature via name mapping: '{group_title}' -> Feature ID {feature_id}")
                                        break
                                    # Also check reverse (group name contained in pattern for shorter group names)
                                    elif len(group_lower) > 3 and group_lower in name_pattern:
                                        found_feature_ids.add(feature_id)
                                        print(f"[EVAL] Matched feature via reverse name mapping: '{group_title}' -> Feature ID {feature_id}")
                                        break
                    
                    print(f"[EVAL] Screenshot tool analysis found {len(found_feature_ids)} unique features from {len(screenshots_data)} groups")
                
                except Exception as e:
                    print(f"[EVAL] Screenshot tool analysis failed: {e}")
                    # Fall back to text extraction if screenshot analysis fails
                    found_feature_ids.update(metrics["found_feature_ids"])
            else:
                # No screenshots found, fall back to text extraction
                found_feature_ids.update(metrics["found_feature_ids"])
                print(f"[EVAL] No screenshot data available, using text extraction: {len(found_feature_ids)} features")
            
            result.found_feature_ids = list(found_feature_ids)
            
            # Check correct features
            correct_features = set(test_config.get("correct_features", []))
            result.correct_features_found = len(correct_features.intersection(found_feature_ids))
            
            print(f"[EVAL] Feature matching: {result.correct_features_found}/{len(correct_features)} correct features found")
            if correct_features and found_feature_ids:
                print(f"[EVAL] Expected: {list(correct_features)}")
                print(f"[EVAL] Found: {list(found_feature_ids)}")
                print(f"[EVAL] Matches: {list(correct_features.intersection(found_feature_ids))}")
            
            # Calculate retrieval rate if enabled in test config
            if test_config.get("expected_behaviors", {}).get("calculate_retrieval_rate", False):
                await self._calculate_retrieval_rate(result, test_config, found_feature_ids, screenshots_data)
            
            # **NEW: ChatGPT scoring if enabled in test config**
            if test_config.get("expected_behaviors", {}).get("use_chatgpt_scoring", False):
                print("[EVAL] Running ChatGPT scoring evaluation...")
                
                # Determine the primary user question for evaluation
                # Use the last user message or first step as the main question
                primary_question = ""
                if conversation_history:
                    # Find the last user message
                    for msg in reversed(conversation_history):
                        if msg["role"] == "user":
                            primary_question = msg["content"]
                            break
                else:
                    # Fall back to first step if no conversation history
                    if test_config.get("steps"):
                        primary_question = test_config["steps"][0]
                
                if primary_question and conversation_history:
                    try:
                        chatgpt_result = await self.score_with_chatgpt(conversation_history, primary_question)
                        
                        if "error" in chatgpt_result:
                            result.chatgpt_scoring_error = chatgpt_result["error"]
                            print(f"[EVAL] ChatGPT scoring failed: {chatgpt_result['error']}")
                        else:
                            result.chatgpt_relevance_score = chatgpt_result["score"]
                            result.chatgpt_rationale = chatgpt_result["rationale"]
                            print(f"[EVAL] ChatGPT scored conversation: {result.chatgpt_relevance_score:.3f}")
                            print(f"[EVAL] ChatGPT rationale: {result.chatgpt_rationale[:100]}...")
                            
                    except Exception as scoring_error:
                        result.chatgpt_scoring_error = str(scoring_error)
                        print(f"[EVAL] ChatGPT scoring exception: {scoring_error}")
                else:
                    result.chatgpt_scoring_error = "No conversation history or primary question available for scoring"
                    print("[EVAL] ChatGPT scoring skipped: no conversation data")
            
        except Exception as e:
            result.error = str(e)
            print(f"[EVAL] Test execution error: {e}")
        
        finally:
            # Clean up any created tasks to prevent recursion
            for task in created_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass  # Ignore cleanup errors
            
            # Clear session state after each test to prevent accumulation
            ExecutionContext._mock_session_state.clear()
        
        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result
    
    async def run_variant_tests(self, variant_name: str, variant_path: str) -> Dict[str, VariantResults]:
        """Run all tests for a specific variant"""
        variant_prompt = self.load_system_prompt_variant(variant_path)
        variant_results = {}
        
        for test in self.config["tests"]:
            test_name = test["name"]
            runs_per_variant = self.config.get("runs_per_variant", 3)
            
            variant_result = VariantResults(variant_name=variant_name)
            
            # Run the test multiple times
            for run_num in range(runs_per_variant):
                print(f"Running {test_name} - Variant: {variant_name} - Run {run_num + 1}/{runs_per_variant}")
                
                try:
                    # Add timeout to prevent hanging (default 5 minutes per test)
                    result = await asyncio.wait_for(
                        self.run_single_test(test, variant_name, variant_prompt, run_num + 1),
                        timeout=300  # 5 minutes timeout
                    )
                    variant_result.runs.append(result)
                    
                except asyncio.TimeoutError:
                    print(f"[EVAL] Test {test_name} run {run_num + 1} timed out after 5 minutes")
                    timeout_result = TestResult(
                        test_name=test_name,
                        variant_name=variant_name,
                        run_number=run_num + 1,
                        total_correct_features=len(test_config.get("correct_features", [])),
                        error="Test timed out after 5 minutes",
                        execution_time=300.0
                    )
                    variant_result.runs.append(timeout_result)
                    
                except Exception as e:
                    print(f"[EVAL] Test {test_name} run {run_num + 1} failed with error: {e}")
                    error_result = TestResult(
                        test_name=test_name,
                        variant_name=variant_name,
                        run_number=run_num + 1,
                        total_correct_features=len(test_config.get("correct_features", [])),
                        error=str(e),
                        execution_time=0.0
                    )
                    variant_result.runs.append(error_result)
            
            variant_results[test_name] = variant_result
        
        return variant_results
    
    async def run_all_evaluations(self):
        """Run all evaluations for all variants"""
        print(f"Starting evaluation with {len(self.config['variants'])} variants")
        
        try:
            for variant in self.config["variants"]:
                variant_name = variant["name"]
                variant_path = variant["path"]
                
                print(f"\nEvaluating variant: {variant_name}")
                variant_results = await self.run_variant_tests(variant_name, variant_path)
                self.results[variant_name] = variant_results
            
            print("\nEvaluation complete!")
            
        finally:
            # Comprehensive cleanup to ensure proper termination
            print("[EVAL] Performing cleanup...")
            try:
                # Clear all session state
                ExecutionContext._mock_session_state.clear()
                
                # Close any potential database connections
                try:
                    from database_tool import close_db_connection
                    close_db_connection()
                    print("[EVAL] Database connections closed")
                except (ImportError, AttributeError):
                    # close_db_connection might not exist, that's okay
                    pass
                
                # Clean up ChromaDB connections if they exist
                try:
                    from ChromaDB.vector_search_interface import GameDataSearchInterface
                    # Force garbage collection of any search interface instances
                    import gc
                    gc.collect()
                    print("[EVAL] ChromaDB cleanup completed")
                except ImportError:
                    pass
                
                print("[EVAL] Cleanup completed successfully")
                
            except Exception as cleanup_error:
                print(f"[EVAL] Warning: Cleanup encountered an error: {cleanup_error}")
                # Don't raise the cleanup error, just log it
    
    def generate_report(self, output_path: str):
        """Generate a comprehensive report of all evaluation results"""
        report = {
            "evaluation_date": datetime.now().isoformat(),
            "config": self.config,
            "results": {}
        }
        
        for variant_name, test_results in self.results.items():
            variant_report = {}
            
            for test_name, variant_result in test_results.items():
                test_report = {
                    "individual_runs": [asdict(run) for run in variant_result.runs],
                    "aggregate_metrics": variant_result.aggregate_metrics()
                }
                variant_report[test_name] = test_report
            
            report["results"][variant_name] = variant_report
        
        # Save detailed JSON report
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        # Generate summary report
        summary_path = output_path.replace('.json', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("EVALUATION SUMMARY REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Evaluation Date: {report['evaluation_date']}\n")
            f.write(f"Total Variants: {len(self.config['variants'])}\n")
            f.write(f"Total Tests: {len(self.config['tests'])}\n")
            f.write(f"Runs per Variant: {self.config.get('runs_per_variant', 3)}\n\n")
            
            for variant_name, test_results in self.results.items():
                f.write(f"\nVARIANT: {variant_name}\n")
                f.write("-" * 40 + "\n")
                
                for test_name, variant_result in test_results.items():
                    f.write(f"\n  Test: {test_name}\n")
                    metrics = variant_result.aggregate_metrics()
                    
                    if metrics.get("all_runs_failed"):
                        f.write("    All runs failed!\n")
                    else:
                        f.write(f"    Success Rate: {metrics['successful_runs']}/{metrics['total_runs']}\n")
                        f.write(f"    Screenshot Production Rate: {metrics['screenshot_production_rate']:.2%}\n")
                        f.write(f"    Avg Screenshots: {metrics['avg_screenshot_count']:.1f}\n")
                        if metrics.get('avg_screenshot_relevance'):
                            f.write(f"    Avg Screenshot Relevance: {metrics['avg_screenshot_relevance']:.3f}\n")
                        if metrics.get('avg_feature_relevance'):
                            f.write(f"    Avg Feature Relevance: {metrics['avg_feature_relevance']:.3f}\n")
                        f.write(f"    Avg Correct Features Found: {metrics['avg_correct_features_found']:.1f}\n")
                        if metrics.get('avg_total_available_screenshots'):
                            f.write(f"    Avg Total Available Screenshots: {metrics['avg_total_available_screenshots']:.1f}\n")
                        if metrics.get('avg_retrieval_rate'):
                            f.write(f"    Avg Retrieval Rate: {metrics['avg_retrieval_rate']:.3f} ({metrics['avg_retrieval_rate']:.1%})\n")
                        if metrics.get('avg_screenshots_retrieved_for_correct_features'):
                            f.write(f"    Avg Screenshots Retrieved for Correct Features: {metrics['avg_screenshots_retrieved_for_correct_features']:.1f}\n")
                        f.write(f"    Avg Execution Time: {metrics['avg_execution_time']:.2f}s\n")
                        # ChatGPT scoring metrics
                        if metrics.get('chatgpt_scoring_success_rate') is not None:
                            f.write(f"    ChatGPT Scoring Success Rate: {metrics['chatgpt_scoring_success_rate']:.2%}\n")
                        if metrics.get('avg_chatgpt_relevance_score') is not None:
                            f.write(f"    Avg ChatGPT Relevance Score: {metrics['avg_chatgpt_relevance_score']:.3f}\n")
        
        print(f"\nReports saved to:\n  - {output_path}\n  - {summary_path}")

    async def _calculate_retrieval_rate(self, result: TestResult, test_config: Dict, found_feature_ids: set, screenshots_data: List):
        """Calculate screenshot retrieval rate for correct features"""
        try:
            correct_features = set(test_config.get("correct_features", []))
            
            if not correct_features:
                print("[EVAL] No correct features specified for retrieval rate calculation")
                return
            
            # Query database for total screenshots available for correct features
            feature_ids_str = "', '".join(correct_features)
            query = f"""
            SELECT feature_id, COUNT(*) as screenshot_count
            FROM screenshot_feature_xref 
            WHERE feature_id IN ('{feature_ids_str}')
            GROUP BY feature_id
            """
            
            print(f"[EVAL] Querying database for screenshot counts: {query}")
            
            # Execute the query using the underlying SQL function
            query_result = run_sql_query(query)
            
            total_available = 0
            if query_result and 'rows' in query_result:
                for row in query_result['rows']:
                    if len(row) >= 2:
                        feature_id = str(row[0])
                        count = int(row[1])
                        total_available += count
                        print(f"[EVAL] Feature {feature_id} has {count} screenshots available")
            
            result.total_available_screenshots = total_available
            
            # Count screenshots retrieved for correct features
            screenshots_for_correct_features = 0
            
            if screenshots_data:
                # Get the intersection of found features and correct features
                correctly_found_features = correct_features.intersection(found_feature_ids)
                
                if correctly_found_features:
                    # Query for screenshots that belong to the correctly found features and were actually retrieved
                    retrieved_screenshot_ids = []
                    
                    # Extract screenshot IDs from the retrieved data
                    for group in screenshots_data:
                        if isinstance(group, dict) and "screenshot_data" in group:
                            for screenshot in group["screenshot_data"]:
                                if isinstance(screenshot, dict) and "screenshot_id" in screenshot:
                                    retrieved_screenshot_ids.append(screenshot["screenshot_id"])
                    
                    if retrieved_screenshot_ids:
                        # Query to count how many of the retrieved screenshots belong to correct features
                        screenshot_ids_str = "', '".join(retrieved_screenshot_ids)
                        feature_match_query = f"""
                        SELECT COUNT(*) as matching_count
                        FROM screenshot_feature_xref 
                        WHERE screenshot_id IN ('{screenshot_ids_str}')
                        AND feature_id IN ('{feature_ids_str}')
                        """
                        
                        match_result = run_sql_query(feature_match_query)
                        
                        if match_result and 'rows' in match_result and match_result['rows']:
                            screenshots_for_correct_features = int(match_result['rows'][0][0])
            
            result.screenshots_retrieved_for_correct_features = screenshots_for_correct_features
            
            # Calculate retrieval rate
            if total_available > 0:
                result.retrieval_rate = screenshots_for_correct_features / total_available
            else:
                result.retrieval_rate = 0.0
            
            print(f"[EVAL] Retrieval rate calculation:")
            print(f"[EVAL]   Screenshots retrieved for correct features: {screenshots_for_correct_features}")
            print(f"[EVAL]   Total screenshots available for correct features: {total_available}")
            print(f"[EVAL]   Retrieval rate: {result.retrieval_rate:.3f} ({result.retrieval_rate:.1%})")
            
        except Exception as e:
            print(f"[EVAL] Error calculating retrieval rate: {e}")
            result.total_available_screenshots = 0
            result.retrieval_rate = 0.0
            result.screenshots_retrieved_for_correct_features = 0

async def main():
    """Main entry point for running evaluations"""
    if len(sys.argv) < 2:
        print("Usage: python eval_framework.py <config_file>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    try:
        # Run evaluation in a separate task group to prevent recursion
        async def run_evaluation():
            framework = EvalFramework(config_path)
            await framework.run_all_evaluations()
            
            # Generate report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_name = os.path.splitext(os.path.basename(config_path))[0]
            report_path = f"evals/reports/eval_report_{config_name}_{timestamp}.json"
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            framework.generate_report(report_path)
            return True
        
        # Run with timeout and proper cleanup
        result = await asyncio.wait_for(run_evaluation(), timeout=1800)  # 30 minutes max
        
        if result:
            print("[EVAL] All evaluations completed successfully!")
        
    except asyncio.TimeoutError:
        print("[EVAL] Evaluation timed out after 30 minutes")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[EVAL] Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[EVAL] Evaluation failed with error: {e}")
        sys.exit(1)
    finally:
        # Force cleanup of all pending tasks to prevent recursion
        print("[EVAL] Cleaning up async tasks...")
        try:
            # Get all tasks and cancel them safely
            pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            
            if pending_tasks:
                print(f"[EVAL] Cancelling {len(pending_tasks)} pending tasks...")
                
                # Cancel tasks without recursion
                for task in pending_tasks:
                    task.cancel()
                
                # Wait briefly for cancellation to complete
                try:
                    await asyncio.wait(pending_tasks, timeout=2.0, return_when=asyncio.ALL_COMPLETED)
                except asyncio.TimeoutError:
                    print("[EVAL] Some tasks did not cancel within timeout")
                except Exception as cleanup_error:
                    print(f"[EVAL] Task cleanup error: {cleanup_error}")
            
            print("[EVAL] Task cleanup completed")
            
        except Exception as final_cleanup_error:
            print(f"[EVAL] Final cleanup error: {final_cleanup_error}")
        
        print("[EVAL] Exiting evaluation framework")
        # Force exit to ensure termination
        os._exit(0)  # Use os._exit to force immediate termination

if __name__ == "__main__":
    asyncio.run(main()) 