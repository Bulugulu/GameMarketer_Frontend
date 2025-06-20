import os
import uuid
import streamlit as st
from typing import List, Dict, Any
from database_tool import run_sql_query
from .config import get_screenshot_config
from .r2_client import get_r2_client

def retrieve_screenshots_for_display(screenshot_ids: List[str], feature_keywords: List[str] = None) -> Dict[str, Any]:
    """
    Retrieves and prepares screenshots for display based on screenshot_ids.
    This function is called by the agent via the tool.
    
    Screenshots are now grouped by feature_id and game_id combination to ensure
    features with the same name from different games are displayed separately.
    Each group includes the game name as a subtitle for better organization.
    
    The function handles path resolution by combining the database's relative paths 
    (e.g., "uploads/folder/file.png") with the base "screenshots" directory to create 
    full paths (e.g., "screenshots/uploads/folder/file.png").
    
    Enhanced with video tracking: now includes video information for each screenshot.
    Enhanced with R2 support: can serve screenshots from R2 or local filesystem.
    Enhanced with game information: displays game names as subtitles in UI sections.
    """
    print(f"[DEBUG] retrieve_screenshots_for_display called with {len(screenshot_ids)} screenshot IDs")
    
    # Get screenshot configuration
    screenshot_config = get_screenshot_config()
    print(f"[DEBUG] Screenshot serving mode: {screenshot_config['mode']}")
    
    # Enhanced query to include video information and game details
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
        f.feature_id,
        f.game_id::text,
        g.name as game_name,
        sc.screen_name,
        -- Video tracking fields
        s.video_timestamp_seconds,
        s.screenshot_timestamp,
        v.video_id::text,
        v.video_path,
        v.title as video_title,
        v.youtube_url,
        v.duration_seconds,
        -- Alternative video mapping via cross-reference table
        svx.video_timestamp_seconds as xref_timestamp,
        svx.confidence as xref_confidence
    FROM screenshots s
    LEFT JOIN screenshot_feature_xref sfx ON s.screenshot_id = sfx.screenshot_id
    LEFT JOIN features_game f ON sfx.feature_id = f.feature_id
    LEFT JOIN games g ON f.game_id = g.game_id
    LEFT JOIN screens sc ON s.screen_id = sc.screen_id
    -- Join with video cross-reference table (for many-to-many relationship)
    LEFT JOIN screenshot_video_xref svx ON s.screenshot_id = svx.screenshot_id
    LEFT JOIN videos v ON svx.video_id = v.video_id
    WHERE s.screenshot_id IN ('{"','".join(screenshot_ids)}')
    ORDER BY COALESCE(g.name, 'Unknown Game'), COALESCE(f.name, 'Untagged Screenshots'), s.caption
    """
    
    print(f"[DEBUG] Executing SQL query for screenshot retrieval with video tracking")
    
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
        
        # Group screenshots by feature_id + game_id combination, handling video duplicates
        screenshot_groups = {}
        processed_count = 0
        
        # Initialize R2 client if needed
        r2_client = None
        if screenshot_config['is_r2']:
            r2_client = get_r2_client()
            if not r2_client.is_configured():
                print("[WARNING] R2 mode selected but R2 client not configured. Falling back to local mode.")
                screenshot_config = {"mode": "local", "is_r2": False, "is_local": True}
        
        for row in rows:
            try:
                row_dict = dict(zip(columns, row))
                feature_name = row_dict.get("feature_name") or "Unknown Feature"
                feature_id = row_dict.get("feature_id")
                game_id = row_dict.get("game_id")
                game_name = row_dict.get("game_name") or "Unknown Game"
                screenshot_id = row_dict.get("screenshot_id", "")
                
                # Create a unique group key based on feature_id and game_id
                # For untagged screenshots, use a special key
                if feature_id and game_id:
                    group_key = f"{feature_id}_{game_id}"
                else:
                    # Handle untagged screenshots - group by game if available
                    if game_id:
                        group_key = f"untagged_{game_id}"
                        feature_name = "Untagged Screenshots"
                        game_name = row_dict.get("game_name") or "Unknown Game"
                    else:
                        group_key = "untagged_unknown"
                        feature_name = "Untagged Screenshots"
                        game_name = "Unknown Game"
                
                if group_key not in screenshot_groups:
                    screenshot_groups[group_key] = {
                        "screenshots": {},
                        "feature_name": feature_name,
                        "feature_id": feature_id,
                        "game_id": game_id,
                        "game_name": game_name
                    }
                
                # Get the path from database (relative path)
                screenshot_path = row_dict.get("path", "")
                
                if not screenshot_path:
                    print(f"[WARNING] No path found for screenshot {screenshot_id}")
                    continue
                
                # Handle different serving modes
                if screenshot_config['is_r2']:
                    # R2 mode - generate presigned URL
                    # Normalize path separators for R2
                    normalized_path = screenshot_path.replace('\\', '/').replace('//', '/')
                    
                    # Generate presigned URL
                    presigned_url = r2_client.get_screenshot_url(normalized_path)
                    if not presigned_url:
                        print(f"[WARNING] Failed to generate R2 URL for {normalized_path}")
                        continue
                    
                    valid_path = presigned_url
                    print(f"[DEBUG] Generated R2 URL for {normalized_path}")
                    
                else:
                    # Local mode - construct file system path
                    # Normalize path separators to avoid mixed separators on Windows
                    normalized_path = screenshot_path.replace('\\', '/').replace('//', '/')
                    full_screenshot_path = os.path.normpath(os.path.join("screenshots", normalized_path))
                    
                    valid_path = full_screenshot_path
                    
                    # Check if path exists, if not try alternative extension
                    if full_screenshot_path and not os.path.exists(full_screenshot_path):
                        if screenshot_path.lower().endswith('.jpg'):
                            alternative_relative_path = normalized_path[:-4] + '.png'
                            alternative_full_path = os.path.normpath(os.path.join("screenshots", alternative_relative_path))
                            if os.path.exists(alternative_full_path):
                                valid_path = alternative_full_path
                                print(f"[INFO] Using PNG instead of JPG for {os.path.basename(screenshot_path)}")
                        elif screenshot_path.lower().endswith('.png'):
                            alternative_relative_path = normalized_path[:-4] + '.jpg'
                            alternative_full_path = os.path.normpath(os.path.join("screenshots", alternative_relative_path))
                            if os.path.exists(alternative_full_path):
                                valid_path = alternative_full_path
                                print(f"[INFO] Using JPG instead of PNG for {os.path.basename(screenshot_path)}")
                    
                    # Only process valid paths for local mode
                    if not (valid_path and os.path.exists(valid_path)):
                        print(f"[WARNING] Screenshot path not found: {valid_path}")
                        # Additional debug info for troubleshooting
                        print(f"[DEBUG] Original path from DB: {screenshot_path}")
                        print(f"[DEBUG] Normalized path: {normalized_path}")
                        print(f"[DEBUG] Full constructed path: {full_screenshot_path}")
                        continue
                
                # Handle video information - determine the best video source
                video_info = None
                
                # Check if we have video information
                video_path = row_dict.get("video_path")
                video_timestamp = row_dict.get("video_timestamp_seconds") or row_dict.get("xref_timestamp")
                
                if video_path and video_timestamp is not None:
                    if screenshot_config['is_r2']:
                        # R2 mode - generate presigned URL for video
                        normalized_video_path = video_path.replace('\\', '/').replace('//', '/')
                        video_presigned_url = r2_client.get_screenshot_url(normalized_video_path)
                        full_video_path = video_presigned_url or video_path  # Fallback to original path
                    else:
                        # Local mode - construct full video path
                        normalized_video_path = video_path.replace('\\', '/').replace('//', '/')
                        full_video_path = os.path.normpath(os.path.join("screenshots", normalized_video_path))
                    
                    print(f"[DEBUG] Video info found for screenshot {screenshot_id}:")
                    print(f"  - Raw video_path from DB: {video_path}")
                    print(f"  - Normalized video path: {normalized_video_path}")
                    print(f"  - Full video path: {full_video_path}")
                    print(f"  - Video timestamp: {video_timestamp}")
                    
                    if screenshot_config['is_local']:
                        print(f"  - File exists: {os.path.exists(full_video_path)}")
                    
                    video_info = {
                        "video_id": row_dict.get("video_id"),
                        "video_path": full_video_path,
                        "video_timestamp_seconds": int(video_timestamp),
                        "video_title": row_dict.get("video_title"),
                        "youtube_url": row_dict.get("youtube_url"),
                        "duration_seconds": row_dict.get("duration_seconds"),
                        "confidence": row_dict.get("xref_confidence", 1.0)
                    }
                
                # Check if this screenshot is already processed (due to multiple video mappings)
                if screenshot_id in screenshot_groups[group_key]["screenshots"]:
                    # If we have better video info, update it
                    existing_screenshot = screenshot_groups[group_key]["screenshots"][screenshot_id]
                    if video_info and (not existing_screenshot.get("video_info") or 
                                     video_info.get("confidence", 1.0) > existing_screenshot.get("video_info", {}).get("confidence", 0.0)):
                        existing_screenshot["video_info"] = video_info
                else:
                    # Add new screenshot entry
                    screenshot_groups[group_key]["screenshots"][screenshot_id] = {
                        "path": valid_path,
                        "caption": row_dict.get("caption", ""),
                        "screenshot_id": screenshot_id,
                        "elements": row_dict.get("elements", {}),
                        "screen_name": row_dict.get("screen_name", ""),
                        "video_info": video_info,
                        "serving_mode": screenshot_config['mode']  # Add serving mode info
                    }
                    processed_count += 1
                    
            except Exception as e:
                print(f"[ERROR] Error processing row: {e}")
                continue
        
        print(f"[DEBUG] Processed {processed_count} unique screenshots into {len(screenshot_groups)} feature groups")
        
        # Prepare screenshots for UI
        screenshots_for_ui = []
        retrieved_entries_info = []
        
        for group_key, group_data in screenshot_groups.items():
            screenshots = list(group_data["screenshots"].values())
            if not screenshots:
                continue
            
            feature_name = group_data["feature_name"]
            game_name = group_data["game_name"]
            feature_id = group_data["feature_id"]
            game_id = group_data["game_id"]
            
            # Prepare data for UI including video info
            screenshot_data = []
            for s in screenshots:
                screenshot_entry = {
                    "path": s["path"],
                    "caption": s["caption"],
                    "screenshot_id": s["screenshot_id"],
                    "elements": s["elements"],
                    "screen_name": s["screen_name"],
                    "serving_mode": s["serving_mode"]
                }
                
                # Add video information if available
                if s.get("video_info"):
                    screenshot_entry["video_info"] = s["video_info"]
                
                screenshot_data.append(screenshot_entry)
            
            image_paths = [s["path"] for s in screenshots]
            
            screenshots_for_ui.append({
                "group_title": feature_name,
                "game_name": game_name,  # Add game name for subtitle display
                "feature_id": feature_id,  # Add feature_id for identification
                "game_id": game_id,  # Add game_id for identification
                "image_paths": image_paths,
                "group_type": "feature",  # Add identifier for UI handling
                "screenshot_data": screenshot_data,  # Include full screenshot data with video info
                "serving_mode": screenshot_config['mode']  # Add serving mode to group
            })
            
            # Prepare info for agent
            video_count = sum(1 for s in screenshots if s.get("video_info"))
            retrieved_entries_info.append({
                "feature_name": feature_name,
                "game_name": game_name,  # Add game name to info
                "feature_id": feature_id,  # Add feature_id to info
                "game_id": game_id,  # Add game_id to info
                "screenshot_count": len(screenshots),
                "video_enabled_count": video_count,
                "captions": [s["caption"] for s in screenshots if s.get("caption")],
                "elements": [s["elements"] for s in screenshots if s.get("elements")],
                "screen_names": list(set([s["screen_name"] for s in screenshots if s.get("screen_name")])),
                "serving_mode": screenshot_config['mode']
            })
        
        print(f"[DEBUG] Returning {len(screenshots_for_ui)} groups for UI display")
        print(f"[DEBUG] Screenshots served via: {screenshot_config['mode']}")
        
        return {
            "message_for_agent": f"Retrieved {processed_count} screenshots for display across {len(screenshot_groups)} features. Screenshots served via {screenshot_config['mode']}.",
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