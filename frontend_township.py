import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
from enum import Enum
from typing import List, Dict, Any
import json
import os.path
import uuid

# Load environment variables from .env.local
load_dotenv(".env.local")

# Initialize OpenAI client
API_KEY = os.environ.get("OPENAI_API_KEY")
CLIENT = None
MODEL_NAME = "gpt-4.1" # Or gpt-4-turbo, ensure it's a model that supports tool calling well

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

# Tool definition for the LLM
tools = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_screenshots_for_display",
            "description": "After identifying relevant screenshots (e.g., using SQL queries via run_sql_query), use this tool to retrieve and prepare screenshot data for those screenshots to be shown to the user. You must provide specific screenshot IDs obtained from the SQL query results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "screenshot_ids": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "A list of exact screenshot UUIDs for which to retrieve screenshots. These IDs should primarily come from the results of a previous `run_sql_query` tool call."
                    },
                    "feature_keywords": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional. Specific feature keywords to ensure relevance if screenshot IDs are ambiguous, though IDs from SQL should be fairly specific."
                    }
                },
                "required": ["screenshot_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": "Runs a SQL SELECT query against the Township PostgreSQL database and returns the results. Use this to fetch specific data points when the user's query implies direct database access is needed. Provide the complete SQL query as a string. You can query tables like 'screenshots', 'screens', 'features_game', etc. according to the Township database schema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query to execute. Example: \"SELECT screen_name, description FROM screens WHERE game_id = (SELECT game_id FROM games WHERE name = 'Township');\""
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def get_chatgpt_response(prompt_text, conversation_history):
    if not CLIENT:
        return "Error: OpenAI client not initialized. API key may be missing."

    messages = [
        {
  "role": "system",
  "content": 
"""
    You are an expert data-analyst and SQL assistant for the mobile game Township.
Your job is to find implementation examples (screenshots) for specific features that the user is interested  in.

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
   - Ask if user wants to see images, then call retrieve_screenshots_for_display with the UUIDs.

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
- When you decide to use a tool, state exactly which tool and parameters you will use, then execute the call.
- If you don't know the answer, respond: "I'm not sure – let's try another angle.
"""
}
    ]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": prompt_text})

    try:
        response = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=5024,
            temperature=0.7,
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            available_functions = {
                "retrieve_screenshots_for_display": retrieve_screenshots_for_display,
                "run_sql_query": run_sql_query
            }
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                if function_to_call:
                    function_args_str = tool_call.function.arguments
                    try:
                        function_args = json.loads(function_args_str)
                        
                        kwargs_for_function = {}
                        if function_name == "retrieve_screenshots_for_display":
                            kwargs_for_function["screenshot_ids"] = function_args.get("screenshot_ids", [])
                            kwargs_for_function["feature_keywords"] = function_args.get("feature_keywords")
                        elif function_name == "run_sql_query":
                            kwargs_for_function["query"] = function_args.get("query")
                            print(f"[DEBUG LOG] Attempting to run SQL query from LLM: {kwargs_for_function['query']}") # Log the query
                        
                        tool_function_response_data = function_to_call(**kwargs_for_function)

                        # Log result of run_sql_query
                        if function_name == "run_sql_query":
                            if "error" in tool_function_response_data:
                                print(f"[DEBUG LOG] SQL query failed. Error: {tool_function_response_data['error']}")
                            else:
                                row_count = len(tool_function_response_data.get("rows", []))
                                print(f"[DEBUG LOG] SQL query successful. Returned {row_count} rows. Columns: {tool_function_response_data.get('columns')}")
                                
                                # Fix UUID serialization issues - convert UUID objects to strings
                                if "rows" in tool_function_response_data:
                                    for i, row in enumerate(tool_function_response_data["rows"]):
                                        tool_function_response_data["rows"][i] = [str(cell) if isinstance(cell, uuid.UUID) else cell for cell in row]

                        if function_name == "retrieve_screenshots_for_display":
                            st.session_state.screenshots_to_display = tool_function_response_data.get("screenshots_for_ui", [])
                            llm_tool_response_content = json.dumps({
                                "message": tool_function_response_data.get("message_for_llm"),
                                "retrieved_screenshot_details": tool_function_response_data.get("retrieved_entries_info")
                            })
                        else: # For run_sql_query or other future tools
                            llm_tool_response_content = json.dumps(tool_function_response_data)

                        if len(llm_tool_response_content) > 4000:
                            llm_tool_response_content = json.dumps({"message": "Tool response too long, content truncated."})

                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": llm_tool_response_content,
                        })
                    except json.JSONDecodeError:
                        st.error(f"Error decoding JSON arguments from LLM: {function_args_str}")
                        messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps({"error": "Invalid arguments format from LLM."})})
                        continue
                    except Exception as e:
                        st.error(f"Error executing tool {function_name}: {e}")
                        messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": json.dumps({"error": str(e)})})
                        continue
            
            second_response = CLIENT.chat.completions.create(model=MODEL_NAME, messages=messages)
            return second_response.choices[0].message.content
        else:
            return response_message.content
    except Exception as e:
        if "Unrecognized request argument supplied: tools" in str(e):
            st.error(f"Error calling OpenAI API: {e}. Your current model '{MODEL_NAME}' might not support tools. Try 'gpt-4o', 'gpt-4-turbo', or 'gpt-3.5-turbo-0125'.")
            return "Sorry, API error related to tool usage. Model might need an update."
        st.error(f"Error calling OpenAI API: {e}")
        return "Sorry, I encountered an error."

from database_tool import run_sql_query

def retrieve_screenshots_for_display(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Retrieves and prepares screenshots for display based on screenshot_ids.
    This function is called by the LLM via tool calling.
    """
    print(f"[TOOL CALL] retrieve_screenshots_for_display called by LLM.")
    if screenshot_ids: print(f"  Screenshot IDs: {screenshot_ids}")
    if feature_keywords: print(f"  Feature Keywords: {feature_keywords}")
    
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
                "message_for_llm": f"Error retrieving screenshots: {result['error']}",
                "screenshots_for_ui": [],
                "retrieved_entries_info": []
            }
        
        if not result.get("rows"):
            return {
                "message_for_llm": "No screenshots found with the provided IDs.",
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
            
            # Prepare info for LLM
            retrieved_entries_info.append({
                "screen_name": screen_name,
                "screenshot_count": len(screenshots),
                "captions": [s["caption"] for s in screenshots if s.get("caption")],
                "elements": [s["elements"] for s in screenshots if s.get("elements")]
            })
        
        return {
            "message_for_llm": f"Retrieved {len(rows)} screenshots for display across {len(screenshot_groups)} screens.",
            "screenshots_for_ui": screenshots_for_ui,
            "retrieved_entries_info": retrieved_entries_info
        }
        
    except Exception as e:
        print(f"[ERROR] Exception in retrieve_screenshots_for_display: {e}")
        return {
            "message_for_llm": f"Error retrieving screenshots: {str(e)}",
            "screenshots_for_ui": [],
            "retrieved_entries_info": []
        }

def main():
    st.title("Township Feature Analyst Chatbot")

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
                            st.image(img_path, width=800) # Increased from 300 to 600 for higher quality
                        except Exception as e:
                            st.error(f"Error displaying image {img_path}: {e}") # More specific error
                    else:
                        st.warning(f"Missing: {os.path.basename(img_path)}")
            
            st.markdown("---")
            
        st.session_state.screenshots_to_display = []

    if prompt := st.chat_input("Ask about Township features or screens..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        if CLIENT:
            current_conversation_history = [msg for msg in st.session_state.messages[:-1]]
            bot_response_content = get_chatgpt_response(prompt, current_conversation_history)
            st.session_state.messages.append({"role": "assistant", "content": bot_response_content})
            with st.chat_message("assistant"): st.markdown(bot_response_content)
            
            if st.session_state.screenshots_to_display: 
                st.rerun()
        else:
            error_message = "OpenAI client not initialized. Please check your API key."
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"): st.markdown(error_message)

if __name__ == "__main__":
    main() 