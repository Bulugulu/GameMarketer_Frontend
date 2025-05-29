import os
import uuid
import streamlit as st
from typing import List, Dict, Any
from database_tool import run_sql_query

def retrieve_screenshots_for_display(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Retrieves and prepares screenshots for display based on screenshot_ids.
    This function is called by the agent via the tool.
    
    The function handles path resolution by combining the database's relative paths 
    (e.g., "uploads/folder/file.png") with the base "screenshots" directory to create 
    full paths (e.g., "screenshots/uploads/folder/file.png").
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
            
            # Get the path from database (relative path)
            screenshot_path = row_dict.get("path", "")
            
            # Construct full path by joining with base screenshots directory
            if screenshot_path:
                full_screenshot_path = os.path.join("screenshots", screenshot_path)
            else:
                full_screenshot_path = ""
            
            valid_path = full_screenshot_path
            
            # Check if path exists, if not try alternative extension
            if full_screenshot_path and not os.path.exists(full_screenshot_path):
                if screenshot_path.lower().endswith('.jpg'):
                    alternative_relative_path = screenshot_path[:-4] + '.png'
                    alternative_full_path = os.path.join("screenshots", alternative_relative_path)
                    if os.path.exists(alternative_full_path):
                        valid_path = alternative_full_path
                        print(f"[INFO] Using PNG instead of JPG for {os.path.basename(screenshot_path)}")
                elif screenshot_path.lower().endswith('.png'):
                    alternative_relative_path = screenshot_path[:-4] + '.jpg'
                    alternative_full_path = os.path.join("screenshots", alternative_relative_path)
                    if os.path.exists(alternative_full_path):
                        valid_path = alternative_full_path
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