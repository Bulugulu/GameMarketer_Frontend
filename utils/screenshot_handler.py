import os
import uuid
import streamlit as st
from typing import List, Dict, Any
from database_tool import run_sql_query

def retrieve_screenshots_for_display(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Retrieves and prepares screenshots for display based on screenshot_ids.
    This function is called by the agent via the tool.
    
    Screenshots are now grouped by feature name from the features_game table.
    The function handles path resolution by combining the database's relative paths 
    (e.g., "uploads/folder/file.png") with the base "screenshots" directory to create 
    full paths (e.g., "screenshots/uploads/folder/file.png").
    """
    print(f"[DEBUG] retrieve_screenshots_for_display called with {len(screenshot_ids)} screenshot IDs")
    
    # Get screenshot paths from database with feature information
    query = f"""
    SELECT 
        s.screenshot_id::text, 
        s.path, 
        s.caption, 
        s.screen_id::text, 
        s.modal, 
        s.modal_name, 
        s.elements,
        COALESCE(f.name, 'Untagged Screenshots') as feature_name,
        sc.screen_name
    FROM screenshots s
    LEFT JOIN screenshot_feature_xref sfx ON s.screenshot_id = sfx.screenshot_id
    LEFT JOIN features_game f ON sfx.feature_id = f.feature_id
    LEFT JOIN screens sc ON s.screen_id = sc.screen_id
    WHERE s.screenshot_id IN ('{"','".join(screenshot_ids)}')
    ORDER BY COALESCE(f.name, 'Untagged Screenshots'), s.caption
    """
    
    print(f"[DEBUG] Executing SQL query for screenshot retrieval")
    
    try:
        result = run_sql_query(query)
        print(f"[DEBUG] SQL query result keys: {list(result.keys()) if result else 'None'}")
        
        if "error" in result:
            print(f"[ERROR] SQL query error: {result['error']}")
            return {
                "message_for_agent": f"Error retrieving screenshots: {result['error']}",
                "screenshots_for_ui": [],
                "retrieved_entries_info": []
            }
        
        if not result.get("rows"):
            print("[DEBUG] No rows returned from SQL query")
            return {
                "message_for_agent": "No screenshots found with the provided IDs.",
                "screenshots_for_ui": [],
                "retrieved_entries_info": []
            }
        
        # Process screenshots
        columns = result["columns"]
        rows = result["rows"]
        print(f"[DEBUG] Retrieved {len(rows)} rows with columns: {columns}")
        
        # Group screenshots by feature_name
        screenshot_groups = {}
        processed_count = 0
        
        for row in rows:
            try:
            row_dict = dict(zip(columns, row))
                feature_name = row_dict.get("feature_name") or "Unknown Feature"
            
                if feature_name not in screenshot_groups:
                    screenshot_groups[feature_name] = []
            
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
                    screenshot_groups[feature_name].append({
                    "path": valid_path,
                    "caption": row_dict.get("caption", ""),
                    "screenshot_id": row_dict.get("screenshot_id", ""),
                        "elements": row_dict.get("elements", {}),
                        "screen_name": row_dict.get("screen_name", "")
                    })
                    processed_count += 1
                else:
                    print(f"[WARNING] Screenshot path not found: {valid_path}")
                    
            except Exception as e:
                print(f"[ERROR] Error processing row: {e}")
                continue
        
        print(f"[DEBUG] Processed {processed_count} screenshots into {len(screenshot_groups)} feature groups")
        
        # Prepare screenshots for UI
        screenshots_for_ui = []
        retrieved_entries_info = []
        
        for feature_name, screenshots in screenshot_groups.items():
            if not screenshots:
                continue
                
            image_paths = [s["path"] for s in screenshots]
            
            screenshots_for_ui.append({
                "group_title": feature_name,
                "image_paths": image_paths,
                "group_type": "feature"  # Add identifier for UI handling
            })
            
            # Prepare info for agent
            retrieved_entries_info.append({
                "feature_name": feature_name,
                "screenshot_count": len(screenshots),
                "captions": [s["caption"] for s in screenshots if s.get("caption")],
                "elements": [s["elements"] for s in screenshots if s.get("elements")],
                "screen_names": list(set([s["screen_name"] for s in screenshots if s.get("screen_name")]))
            })
        
        print(f"[DEBUG] Returning {len(screenshots_for_ui)} groups for UI display")
        
        return {
            "message_for_agent": f"Retrieved {processed_count} screenshots for display across {len(screenshot_groups)} features.",
            "screenshots_for_ui": screenshots_for_ui,
            "retrieved_entries_info": retrieved_entries_info
        }
        
    except Exception as e:
        print(f"[ERROR] Exception in retrieve_screenshots_for_display: {e}")
        import traceback
        traceback.print_exc()
        return {
            "message_for_agent": f"Error retrieving screenshots: {str(e)}",
            "screenshots_for_ui": [],
            "retrieved_entries_info": []
        } 