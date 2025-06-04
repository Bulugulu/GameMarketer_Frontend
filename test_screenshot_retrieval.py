#!/usr/bin/env python3
"""
Test script to check screenshot retrieval with video information
"""
import os
from utils.screenshot_handler import retrieve_screenshots_for_display
from database_tool import run_sql_query

def test_screenshot_with_video():
    """Test retrieving screenshots that should have video information"""
    
    print("=== Screenshot + Video Retrieval Test ===\n")
    
    # First, find some screenshots that have video associations
    query = """
    SELECT 
        s.screenshot_id::text,
        s.path,
        s.caption,
        v.video_path,
        svx.video_timestamp_seconds,
        v.title as video_title
    FROM screenshots s
    JOIN screenshot_video_xref svx ON s.screenshot_id = svx.screenshot_id
    JOIN videos v ON svx.video_id = v.video_id
    WHERE v.video_path IS NOT NULL 
    AND svx.video_timestamp_seconds IS NOT NULL
    LIMIT 5
    """
    
    print("🔍 Finding screenshots with video associations...")
    result = run_sql_query(query)
    
    if "error" in result:
        print(f"❌ Database error: {result['error']}")
        return
    
    if not result.get("rows"):
        print("❌ No screenshots with video associations found")
        return
    
    print(f"✅ Found {len(result['rows'])} screenshots with video info\n")
    
    # Test retrieving these screenshots
    screenshot_ids = [row[0] for row in result["rows"]]
    
    print(f"📸 Testing retrieval of screenshot IDs: {screenshot_ids}")
    print()
    
    # Call the actual function used by the frontend
    retrieved_data = retrieve_screenshots_for_display(screenshot_ids)
    
    print("📊 Retrieval Results:")
    print(f"   Message: {retrieved_data.get('message_for_agent', 'N/A')}")
    print(f"   Screenshot groups: {len(retrieved_data.get('screenshots_for_ui', []))}")
    print(f"   Entry info count: {len(retrieved_data.get('retrieved_entries_info', []))}")
    print()
    
    # Check the screenshot data in detail
    for i, group in enumerate(retrieved_data.get('screenshots_for_ui', []), 1):
        print(f"🖼️  Group {i}: {group.get('group_title', 'Unknown')}")
        print(f"   Type: {group.get('group_type', 'N/A')}")
        print(f"   Images: {len(group.get('image_paths', []))}")
        
        screenshot_data = group.get('screenshot_data', [])
        print(f"   Screenshot data entries: {len(screenshot_data)}")
        
        # Check video info for each screenshot
        for j, screenshot_info in enumerate(screenshot_data):
            print(f"   📷 Screenshot {j+1}:")
            print(f"      Path: {screenshot_info.get('path', 'N/A')}")
            print(f"      Caption: {screenshot_info.get('caption', 'N/A')[:50]}...")
            
            video_info = screenshot_info.get('video_info')
            if video_info:
                print(f"      🎬 Video Info:")
                print(f"         Video Path: {video_info.get('video_path', 'N/A')}")
                print(f"         Timestamp: {video_info.get('video_timestamp_seconds', 'N/A')} seconds")
                print(f"         Title: {video_info.get('video_title', 'N/A')}")
                print(f"         File exists: {os.path.exists(video_info.get('video_path', ''))}")
            else:
                print(f"      ❌ No video info found")
        print()

if __name__ == "__main__":
    test_screenshot_with_video() 