import streamlit as st
import uuid
from typing import List, Dict, Any
from agents import function_tool
from database_tool import run_sql_query
from .screenshot_handler import retrieve_screenshots_for_display

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