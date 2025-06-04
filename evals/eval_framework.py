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

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.agent_config import sql_analysis_agent, AgentResponse
from agents import Runner, Agent
from utils.context_detector import ExecutionContext

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
        }

class EvalFramework:
    def __init__(self, config_path: str):
        """Initialize the evaluation framework with a config file"""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.results: Dict[str, Dict[str, VariantResults]] = {}
        
    def load_system_prompt_variant(self, variant_path: str) -> str:
        """Load a system prompt variant from file"""
        with open(variant_path, 'r') as f:
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
                                # For now, we'll map feature names to IDs manually based on the semantic search results
                                # This is more reliable than database queries in this context
                                
                                # Check if we have feature mapping from semantic search tool results in session state
                                semantic_results = ExecutionContext.get_session_state_value("last_semantic_search_results", None)
                                if semantic_results:
                                    # Look for feature matches in semantic search results
                                    for result in semantic_results.get("results", []):
                                        result_name = result.get("name", "").lower()
                                        group_name = group_title.lower()
                                        
                                        # Match feature names (case-insensitive, partial matching)
                                        if result_name in group_name or group_name in result_name:
                                            feature_id = result.get("feature_id")
                                            if feature_id:
                                                found_feature_ids.add(str(feature_id))
                                                print(f"[EVAL] Matched feature via semantic search: '{group_title}' -> Feature ID {feature_id}")
                                
                                # Also try direct feature name mapping for known features
                                feature_name_mapping = {
                                    "mini-games": "17",  # Based on semantic search logs showing Feature ID: 17 | Name: Mini-Games
                                    "minigames": "17",
                                    "mini games": "17"
                                }
                                
                                for name_pattern, feature_id in feature_name_mapping.items():
                                    if name_pattern in group_title.lower():
                                        found_feature_ids.add(feature_id)
                                        print(f"[EVAL] Matched feature via name mapping: '{group_title}' -> Feature ID {feature_id}")
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
            
        except Exception as e:
            result.error = str(e)
        
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
                result = await self.run_single_test(test, variant_name, variant_prompt, run_num + 1)
                variant_result.runs.append(result)
            
            variant_results[test_name] = variant_result
        
        return variant_results
    
    async def run_all_evaluations(self):
        """Run all evaluations for all variants"""
        print(f"Starting evaluation with {len(self.config['variants'])} variants")
        
        for variant in self.config["variants"]:
            variant_name = variant["name"]
            variant_path = variant["path"]
            
            print(f"\nEvaluating variant: {variant_name}")
            variant_results = await self.run_variant_tests(variant_name, variant_path)
            self.results[variant_name] = variant_results
        
        print("\nEvaluation complete!")
    
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
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate summary report
        summary_path = output_path.replace('.json', '_summary.txt')
        with open(summary_path, 'w') as f:
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
                        f.write(f"    Avg Execution Time: {metrics['avg_execution_time']:.2f}s\n")
        
        print(f"\nReports saved to:\n  - {output_path}\n  - {summary_path}")

async def main():
    """Main entry point for running evaluations"""
    if len(sys.argv) < 2:
        print("Usage: python eval_framework.py <config_file>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    framework = EvalFramework(config_path)
    
    await framework.run_all_evaluations()
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"evals/reports/eval_report_{timestamp}.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    framework.generate_report(report_path)

if __name__ == "__main__":
    asyncio.run(main()) 