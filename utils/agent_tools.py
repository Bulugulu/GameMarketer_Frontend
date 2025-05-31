import streamlit as st
import uuid
from typing import List, Dict, Any, Optional, Literal
from agents import function_tool
from database_tool import run_sql_query
from .screenshot_handler import retrieve_screenshots_for_display

# Import the ChromaDB vector search interface
try:
    from ChromaDB.vector_search_interface import GameDataSearchInterface
except ImportError:
    GameDataSearchInterface = None
    print("[WARNING] ChromaDB vector search interface not available. Semantic search tool will be disabled.")

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

@function_tool
def semantic_search_tool(
    query: str, 
    content_type: Literal["features", "screenshots", "both"] = "both",
    limit: int = 20,
    game_id: Optional[str] = None,
    feature_ids: Optional[List[str]] = None,
    screenshot_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Performs semantic search across game features and/or screenshots using vector embeddings.
    This tool searches the ChromaDB vector database to find the most semantically similar content
    to the user's query. Use this tool when you need to find relevant content based on meaning
    rather than exact keyword matches.
    
    Args:
        query: The search query to find semantically similar content
        content_type: What to search for - "features", "screenshots", or "both"  
        limit: Maximum number of results to return for each content type (default: 20, increase for broader exploration)
        game_id: Optional filter by specific game ID
        feature_ids: Optional list of specific feature IDs to search within (only for features/both)
        screenshot_ids: Optional list of specific screenshot IDs to search within (only for screenshots/both)
        
    Returns:
        Dictionary containing search results with high-level metadata:
        - For features: feature_id, name, game_id, distance (similarity score)
        - For screenshots: screenshot_id, caption, game_id, distance (similarity score)
        Note: Lower distance values indicate higher similarity.
        IMPORTANT: This is for initial discovery only - use ALL screenshot IDs found via SQL for final display.
    """
    try:
        if GameDataSearchInterface is None:
            return {
                "error": "ChromaDB vector search interface not available. Please ensure ChromaDB is properly set up."
            }
        
        filter_info = []
        if game_id:
            filter_info.append(f"game_id: {game_id}")
        if feature_ids:
            filter_info.append(f"feature_ids: {len(feature_ids)} IDs")
        if screenshot_ids:
            filter_info.append(f"screenshot_ids: {len(screenshot_ids)} IDs")
        
        filter_str = f" | Filters: {', '.join(filter_info)}" if filter_info else ""
        print(f"[DEBUG LOG] Semantic search executed: '{query}' | Type: {content_type} | Limit: {limit}{filter_str}")
        
        # Initialize the search interface
        search_interface = GameDataSearchInterface()
        
        result = {
            "query": query,
            "content_type": content_type,
            "limit": limit
        }
        
        # Add filter information to result
        if game_id:
            result["game_id"] = game_id
        if feature_ids:
            result["feature_ids_filter"] = feature_ids
        if screenshot_ids:
            result["screenshot_ids_filter"] = screenshot_ids
        
        if content_type == "features":
            features = search_interface.search_game_features(
                query, limit=limit, game_id=game_id, feature_ids=feature_ids
            )
            result["features"] = [
                {
                    "feature_id": f["feature_id"],
                    "name": f["name"], 
                    "game_id": f["game_id"],
                    "distance": f["distance"]
                }
                for f in features
            ]
            print(f"[DEBUG LOG] Found {len(result['features'])} similar features")
            
        elif content_type == "screenshots":
            screenshots = search_interface.search_game_screenshots(
                query, limit=limit, game_id=game_id, screenshot_ids=screenshot_ids
            )
            result["screenshots"] = [
                {
                    "screenshot_id": s["screenshot_id"],
                    "caption": s["caption"],
                    "game_id": s["game_id"], 
                    "distance": s["distance"]
                }
                for s in screenshots
            ]
            print(f"[DEBUG LOG] Found {len(result['screenshots'])} similar screenshots")
            
        else:  # both
            all_results = search_interface.search_all_game_content(
                query, limit=limit, game_id=game_id, 
                feature_ids=feature_ids, screenshot_ids=screenshot_ids
            )
            result["features"] = [
                {
                    "feature_id": f["feature_id"],
                    "name": f["name"],
                    "game_id": f["game_id"],
                    "distance": f["distance"]
                }
                for f in all_results.get("features", [])
            ]
            result["screenshots"] = [
                {
                    "screenshot_id": s["screenshot_id"],
                    "caption": s["caption"],
                    "game_id": s["game_id"],
                    "distance": s["distance"]
                }
                for s in all_results.get("screenshots", [])
            ]
            print(f"[DEBUG LOG] Found {len(result.get('features', []))} features and {len(result.get('screenshots', []))} screenshots")
        
        return result
        
    except Exception as e:
        error_result = {"error": f"Exception in semantic search: {str(e)}"}
        print(f"[DEBUG LOG] Exception in semantic search: {str(e)}")
        return error_result 