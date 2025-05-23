import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum
from typing import List, Dict, Any
import json
import os.path
import uuid
import asyncio
import threading

# Import the Agents SDK
from agents import Agent, Runner, function_tool

# Load environment variables from .env.local
load_dotenv(".env.local")

# Initialize OpenAI client
API_KEY = os.environ.get("OPENAI_API_KEY")
CLIENT = None
MODEL_NAME = "gpt-4o"  # Use a model that works well with Agents SDK

# Global variable for the database connection parameters
DB_CONNECTION_PARAMS = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "dbname": os.environ.get("DB_NAME", "township_db"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "port": os.environ.get("DB_PORT", "5432")
}

if API_KEY:
    CLIENT = OpenAI(api_key=API_KEY)
else:
    st.error("OPENAI_API_KEY not found. Please set it in .env.local or as an environment variable.")

# Import the database tool
from database_tool import run_sql_query

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

def retrieve_screenshots_for_display(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Retrieves and prepares screenshots for display based on screenshot_ids.
    This function is called by the agent via the tool.
    """
    # Get screenshot paths from database
    query = f"""
    SELECT screenshot_id::text, path, caption, screen_id::text, modal, modal_name, elements, 
           (SELECT screen_name FROM screens WHERE screens.screen_id = screenshots.screen_id) as screen_name
    FROM screenshots 
    WHERE screenshot_id IN ('{"','".join(screenshot_ids)}')
    """
    
    try:
        result = run_sql_query(query)
        if "error" in result:
            return {
                "message_for_agent": f"Error retrieving screenshots: {result['error']}",
                "screenshots_for_ui": [],
                "retrieved_entries_info": []
            }
        
        if not result.get("rows"):
            return {
                "message_for_agent": "No screenshots found with the provided IDs.",
                "screenshots_for_ui": [],
                "retrieved_entries_info": []
            }
        
        # Process screenshots
        columns = result["columns"]
        rows = result["rows"]
        
        # Group screenshots by screen_name
        screenshot_groups = {}
        for row in rows:
            row_dict = dict(zip(columns, row))
            screen_name = row_dict.get("screen_name") or "Unknown Screen"
            
            if screen_name not in screenshot_groups:
                screenshot_groups[screen_name] = []
            
            # Get the path
            screenshot_path = row_dict.get("path", "")
            valid_path = screenshot_path
            
            # Check if path exists, if not try alternative extension
            if screenshot_path and not os.path.exists(screenshot_path):
                if screenshot_path.lower().endswith('.jpg'):
                    alternative_path = screenshot_path[:-4] + '.png'
                    if os.path.exists(alternative_path):
                        valid_path = alternative_path
                        print(f"[INFO] Using PNG instead of JPG for {os.path.basename(screenshot_path)}")
                elif screenshot_path.lower().endswith('.png'):
                    alternative_path = screenshot_path[:-4] + '.jpg'
                    if os.path.exists(alternative_path):
                        valid_path = alternative_path
                        print(f"[INFO] Using JPG instead of PNG for {os.path.basename(screenshot_path)}")
            
            # If valid path exists, add to the group
            if valid_path and os.path.exists(valid_path):
                screenshot_groups[screen_name].append({
                    "path": valid_path,
                    "caption": row_dict.get("caption", ""),
                    "screenshot_id": row_dict.get("screenshot_id", ""),
                    "elements": row_dict.get("elements", {})
                })
        
        # Prepare screenshots for UI
        screenshots_for_ui = []
        retrieved_entries_info = []
        
        for screen_name, screenshots in screenshot_groups.items():
            if not screenshots:
                continue
                
            image_paths = [s["path"] for s in screenshots]
            
            screenshots_for_ui.append({
                "group_title": screen_name,
                "image_paths": image_paths
            })
            
            # Prepare info for agent
            retrieved_entries_info.append({
                "screen_name": screen_name,
                "screenshot_count": len(screenshots),
                "captions": [s["caption"] for s in screenshots if s.get("caption")],
                "elements": [s["elements"] for s in screenshots if s.get("elements")]
            })
        
        return {
            "message_for_agent": f"Retrieved {len(rows)} screenshots for display across {len(screenshot_groups)} screens.",
            "screenshots_for_ui": screenshots_for_ui,
            "retrieved_entries_info": retrieved_entries_info
        }
        
    except Exception as e:
        print(f"[ERROR] Exception in retrieve_screenshots_for_display: {e}")
        return {
            "message_for_agent": f"Error retrieving screenshots: {str(e)}",
            "screenshots_for_ui": [],
            "retrieved_entries_info": []
        }

# Define the SQL Analysis Agent
sql_analysis_agent = Agent(
    name="SQL Analysis Agent",
    instructions="""
You are an expert data-analyst and SQL assistant for the mobile game Township.
Your job is to find implementation examples (screenshots) for specific features that the user is interested in.

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
""",
    tools=[run_sql_query_tool, retrieve_screenshots_for_display_tool]
)

def get_agent_response(prompt_text, conversation_history):
    """
    Get response from the SQL Analysis Agent using the Agents SDK
    """
    if not CLIENT:
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

def main():
    st.title("Township Feature Analyst Chatbot (Agentic)")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "screenshots_to_display" not in st.session_state:
        st.session_state.screenshots_to_display = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str):
                st.markdown(message["content"])
            else:
                st.markdown(str(message["content"])) 
    
    if st.session_state.screenshots_to_display:
        st.markdown("--- Screenshots ---")
        for screenshot_group in st.session_state.screenshots_to_display:
            group_title = screenshot_group.get("group_title", "Retrieved Screenshots")
            image_paths_for_grid = screenshot_group.get("image_paths", [])
            
            st.write(f"**{group_title}**")
            
            if not image_paths_for_grid:
                st.write("(No images found for this group)")
                st.markdown("---")
                continue

            num_columns = 3
            cols = st.columns(num_columns)
            
            for index, img_path in enumerate(image_paths_for_grid):
                col_index = index % num_columns
                with cols[col_index]:
                    if os.path.exists(img_path):
                        try:
                            st.image(img_path, width=800)
                        except Exception as e:
                            st.error(f"Error displaying image {img_path}: {e}")
                    else:
                        st.warning(f"Missing: {os.path.basename(img_path)}")
            
            st.markdown("---")
            
        st.session_state.screenshots_to_display = []

    if prompt := st.chat_input("Ask about Township features or screens..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)

        if CLIENT:
            current_conversation_history = [msg for msg in st.session_state.messages[:-1]]
            bot_response_content = get_agent_response(prompt, current_conversation_history)
            st.session_state.messages.append({"role": "assistant", "content": bot_response_content})
            with st.chat_message("assistant"): 
                st.markdown(bot_response_content)
            
            if st.session_state.screenshots_to_display: 
                st.rerun()
        else:
            error_message = "OpenAI client not initialized. Please check your API key."
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"): 
                st.markdown(error_message)

if __name__ == "__main__":
    main() 