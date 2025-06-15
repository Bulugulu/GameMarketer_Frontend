import streamlit as st
import asyncio
import threading
from pydantic import BaseModel, Field
from agents import Agent, Runner
from .agent_tools import run_sql_query_tool, retrieve_screenshots_for_display_tool, semantic_search_tool
from .config import get_client

# Pydantic model for structured output
class AgentResponse(BaseModel):
    """Structured response model for meta prompting."""
    user_reponse: str = Field(description="The response to show to the user")
    developer_note: str = Field(default="", description="Internal feedback for developers - issues, improvements, or system insights")

# Define the SQL Analysis Agent
sql_analysis_agent = Agent(
    name="SQL Analysis Agent",
    instructions="""
You are a mobile game market analyst with access to a game features database.

## DATABASE SCHEMA
- games: game_id, name, genre, context
- taxonomy: taxon_id, parent_id, level (domain/category), name, description  
- features_game: feature_id, game_id, name, description
- screenshots: screenshot_id, game_id, caption, elements (JSONB)
- taxon_features_xref: taxon_id, feature_id, confidence
- screenshot_feature_xref: screenshot_id, feature_id, confidence

## TOOLS
1. **semantic_search_tool**: Find features/screenshots by meaning (returns relevance scores 0-1)
2. **run_sql_query_tool**: Precise database queries using feature_ids/screenshot_ids from semantic search
3. **retrieve_screenshots_for_display_tool**: Display screenshots using screenshot_ids

## WORKFLOW
1. Use semantic_search_tool to find relevant content
2. Filter results by relevance score (≥0.6 for quality)
3. Use SQL queries to get detailed data for high-relevance results
4. Retrieve ALL screenshots for selected features (don't limit artificially)
5. Present organized results

## RULES
- Search game name first to get game_id, then filter searches by game_id
- Use semantic search for exploration, SQL for precision
- Always retrieve screenshots after finding relevant features
- Include taxonomy information when relevant
- Provide structured output with user_response and developer_note

Structure your response using AgentResponse model.
""",
    tools=[semantic_search_tool, run_sql_query_tool, retrieve_screenshots_for_display_tool],
    output_type=AgentResponse
)

def get_agent_response(prompt_text, conversation_history):
    """
    Get response from the SQL Analysis Agent using the Agents SDK
    """
    client = get_client()
    if not client:
        return "Error: OpenAI client not initialized. API key may be missing."
    
    try:
        # Convert conversation history to a format suitable for agents
        full_input = ""
        
        # Add conversation history if available - TRUNCATE to prevent context overflow
        if conversation_history:
            # Keep only the last 5 conversation turns to manage context size
            max_history_pairs = 5
            recent_history = conversation_history[-max_history_pairs*2:] if len(conversation_history) > max_history_pairs*2 else conversation_history
            
            history_context = "Previous conversation:\n"
            for msg in recent_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
                    # Truncate very long individual messages
                    if len(content) > 2000:
                        content = content[:2000] + "... [truncated]"
                    history_context += f"{role}: {content}\n"
            history_context += f"\nCurrent question: {prompt_text}"
            full_input = history_context
        else:
            full_input = prompt_text
        
        # Define an async function to run the agent
        async def run_agent_async():
            result = await Runner.run(sql_analysis_agent, full_input)
            return result.final_output
        
        # Run the async function in a new event loop
        try:
            # Use asyncio.run() to create a new event loop and run the agent
            agent_output = asyncio.run(run_agent_async())
            
            # Handle structured output - the agent now returns an AgentResponse object
            if isinstance(agent_output, AgentResponse):
                # Return the structured response as a JSON string for our existing parsing logic
                return {
                    "user_reponse": agent_output.user_reponse,
                    "developer_note": agent_output.developer_note
                }
            else:
                # Fallback for any unexpected response format
                return str(agent_output)
                
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                # If we're in a running event loop, use a thread
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        agent_output = asyncio.run(run_agent_async())
                        # Handle structured output in thread context too
                        if isinstance(agent_output, AgentResponse):
                            result = {
                                "user_reponse": agent_output.user_reponse,
                                "developer_note": agent_output.developer_note
                            }
                        else:
                            result = str(agent_output)
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                
                return result
            else:
                raise e
        
    except Exception as e:
        st.error(f"Error calling Agents SDK: {e}")
        return "Sorry, I encountered an error while processing your request." 