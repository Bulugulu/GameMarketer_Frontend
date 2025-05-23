import streamlit as st
import uuid
import asyncio
import threading
from typing import List, Dict, Any
from agents import Agent, Runner, function_tool
from database_tool import run_sql_query
from .config import get_client
from .screenshot_handler import retrieve_screenshots_for_display

# Define tools using the Agents SDK function_tool decorator
@function_tool
def run_sql_query_tool(query: str) -> Dict[str, Any]:
    """
    Runs a SQL SELECT query against the Township PostgreSQL database and returns the results.
    Use this to fetch specific data points when the user's query implies direct database access is needed.
    Provide the complete SQL query as a string. You can query tables like 'screenshots', 'screens', 
    'features_game', etc. according to the Township database schema.
    
    Args:
        query: The SQL SELECT query to execute
        
    Returns:
        Dictionary containing query results with 'columns' and 'rows' keys, or 'error' if failed
    """
    try:
        result = run_sql_query(query)
        print(f"[DEBUG LOG] SQL query executed: {query}")
        
        if "error" in result:
            print(f"[DEBUG LOG] SQL query failed. Error: {result['error']}")
            return result
        else:
            row_count = len(result.get("rows", []))
            print(f"[DEBUG LOG] SQL query successful. Returned {row_count} rows.")
            
            # Fix UUID serialization issues - convert UUID objects to strings
            if "rows" in result:
                for i, row in enumerate(result["rows"]):
                    result["rows"][i] = [str(cell) if isinstance(cell, uuid.UUID) else cell for cell in row]
            
            return result
            
    except Exception as e:
        error_result = {"error": f"Exception in SQL query execution: {str(e)}"}
        print(f"[DEBUG LOG] Exception in SQL query: {str(e)}")
        return error_result

@function_tool
def retrieve_screenshots_for_display_tool(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    After identifying relevant screenshots (e.g., using SQL queries), use this tool to retrieve and 
    prepare screenshot data for those screenshots to be shown to the user. You must provide specific 
    screenshot IDs obtained from the SQL query results.
    
    Args:
        screenshot_ids: A list of exact screenshot UUIDs for which to retrieve screenshots
        feature_keywords: Optional specific feature keywords to ensure relevance
        
    Returns:
        Dictionary containing screenshots for UI display and metadata
    """
    print(f"[TOOL CALL] retrieve_screenshots_for_display called by agent.")
    if screenshot_ids: 
        print(f"  Screenshot IDs: {screenshot_ids}")
    if feature_keywords: 
        print(f"  Feature Keywords: {feature_keywords}")
    
    result = retrieve_screenshots_for_display(screenshot_ids, feature_keywords)
    
    # Store screenshots for UI display
    if "screenshots_for_ui" in result:
        st.session_state.screenshots_to_display = result["screenshots_for_ui"]
    
    return result

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
Cross-reference tables:
• taxon_features_xref     (taxon_id→taxonomy, feature_id→features_game, confidence)
• screen_feature_xref     (screen_id→screens,  feature_id→features_game)
• screenflow_xref         (from_screen_id→screens, to_screen_id→screens, action_label, ordinal)
• screenshot_feature_xref (screenshot_id→screenshots, feature_id→features_game, confidence, first_tagged)
• taxon_screenshots_xref  (taxon_id→taxonomy, screenshot_id→screenshots, confidence)
• feature_flow_step       (flow_id, feature_id→features_game, step_index, screenshot_id→screenshots,
                           action_label, session_id, title, notes)

Column details:
• elements in screenshots is an array of objects {name, description, type} stored as JSONB.
• screenshot_id is a UUID. Cast with ::text as needed.
• path is a relative URI such as "screenshots/abc.jpg"; prepend the server base-URL if sending to clients.

QUERY STRATEGY

Follow these steps in order for each user question:

1. **Normalize user question**
   - Break the question into concept tokens (e.g. "speed-up", "crop", "T-Cash").
   - Stem/plural-strip but keep original casing for literal matches.
   - Try mapping tokens to taxonomy.name.
   - If you don't find a good fit, try to find synonyms for the terms the user used. Game features are often described in different terms. 
   - If you find too many results, try to narrow the results by showing the user examples of screenshots from feature candidates (one at a time).


2. **Map tokens to taxonomy**
   Example SQL:
   SELECT taxon_id, name
   FROM   taxonomy
   WHERE  name ILIKE ANY (ARRAY[ $1, $2, ... ]);
   - If taxons found, continue; else jump to step 4.

   You can also select * from the taxonomy table to get a list of all the features and subfeatures in our database. 

3. **Expand via taxon_features_xref**
   SELECT DISTINCT feature_id
   FROM   taxon_features_xref
   WHERE  taxon_id IN (<ids from step 2>)
     AND  confidence >= 0.7
   - Store as feature_set_A.

4. **Direct feature lookup (fallback or supplement)**
   SELECT feature_id
   FROM   features_game
   WHERE  game_id = (SELECT game_id FROM games WHERE name = 'Township')
     AND  name ILIKE ANY (ARRAY[ $1, $2, ... ]);
   - Merge these IDs with feature_set_A to get feature_ids.
   - If still empty, go to step 8.

5. **Get relevant screenshots via screenshot_feature_xref**
   SELECT DISTINCT screenshot_id
   FROM   screenshot_feature_xref
   WHERE  feature_id = ANY(:feature_ids)
     AND  confidence >= 0.5
   - Store as candidate_shots.

6. **Intersection/refinement for multi-concept queries**
   - If user mentions multiple independent concepts, repeat steps 2–5 and intersect sets.

7. **Return screenshots & metadata**
   SELECT s.screenshot_id::text, s.path, s.caption, s.elements
   FROM   screenshots s
   WHERE  s.screenshot_id = ANY(:candidate_shots)
   ORDER  BY s.capture_time
   LIMIT  50;
   - If you find relevant screenshots, call retrieve_screenshots_for_display_tool with the UUIDs.

8. **Only if no rows yet:** Do a controlled free-text scan on caption and elements (with LIMIT 50).

───────────────────────────── ⚖️ RULES & TIPS

- Always try steps 1–7 before falling back to step 8.
- Prefer JOINs and lookups over ILIKE or semantic search.
- Cast UUIDs → text only for output or LIKE operations.
- Never select the embedding column unless the user explicitly asks for vector data.
- Avoid SELECT *; list columns needed for the answer.
- Always filter by Township game_id.
- Use LIMIT 50 unless user insists on more.

───────────────────────────── ⚙️ GOOD PRACTICES

- **Schema linking:** match user terms to column names (e.g., "farm" ↔ features_game.name ILIKE '%farm%').
- **Safety:** never interpolate raw user text; always parameterize or sanitize (ILIKE '%' || $1 || '%').
- **Performance:** avoid SELECT *; list only required columns.
- **Explain concepts:** answer conceptual questions directly when possible, without querying the DB.
- **Be truthful:** If the info isn't in the DB, say you don't have it.
- When you find relevant screenshots, always call retrieve_screenshots_for_display_tool to show them to the user.
- Work step by step through the query strategy, and be willing to try multiple approaches if the first doesn't work.
- When sharing screenshots, explain the connection between the user's question and the screenshots. Point out which features and elements in the screenshot fit the user's question. 

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