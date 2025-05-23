import streamlit as st
import asyncio
import threading
from agents import Agent, Runner
from .agents import run_sql_query_tool, retrieve_screenshots_for_display_tool
from .config import get_client

# Define the SQL Analysis Agent
sql_analysis_agent = Agent(
    name="SQL Analysis Agent",
    instructions="""
You are a game analyst and SQL assistant for the mobile game Township.
Your job is to query the database to answer questions and find implementation examples for specific features that the user is interested in.

DATABASE REFERENCE

Tables & key columns:
• games              (game_id PK, name, genre, ...)
• taxonomy           (taxon_id PK, parent_id→taxonomy, level ENUM['category','feature','subfeature'], name, description)
• features_game      (feature_id PK, game_id→games, name, description, first_seen, last_updated, ui_flow)
• screens            (screen_id PK, game_id→games, screen_name, description, first_seen, last_updated, layout_hash)
• screenshots        (screenshot_id PK UUID, path, game_id→games, screen_id→screens,
                      session_id, capture_time, caption, elements JSONB, modal, modal_name,
                      embedding VECTOR, sha256)

QUERY STRATEGY

Follow these steps in order for each user question:

1. **Normalize user question** - Break into concept tokens, map to taxonomy.name
2. **Map tokens to taxonomy** - Use ILIKE queries to find matching taxons
3. **Expand via taxon_features_xref** - Get feature_ids with confidence >= 0.7
4. **Direct feature lookup** - Fallback search in features_game table
5. **Get relevant screenshots** - Use screenshot_feature_xref with confidence >= 0.5
6. **Return screenshots & metadata** - Call retrieve_screenshots_for_display_tool with UUIDs

RULES & TIPS

- Always try steps 1–7 before falling back to free-text search
- Prefer JOINs and lookups over ILIKE or semantic search
- Cast UUIDs → text only for output or LIKE operations
- Always filter by Township game_id
- When you find relevant screenshots, always call retrieve_screenshots_for_display_tool
- Explain the connection between user's question and the screenshots shown

""",
    tools=[run_sql_query_tool, retrieve_screenshots_for_display_tool]
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
        
        # Add conversation history if available
        if conversation_history:
            history_context = "Previous conversation:\n"
            for msg in conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
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
            return asyncio.run(run_agent_async())
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                # If we're in a running event loop, use a thread
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        result = asyncio.run(run_agent_async())
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