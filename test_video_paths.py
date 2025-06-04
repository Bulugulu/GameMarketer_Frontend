#!/usr/bin/env python3
"""
Test script to debug video path issues
"""
import os
from database_tool import run_sql_query

def test_video_paths():
    """Test video paths in database vs file system"""
    
    print("=== Video Path Debug Test ===\n")
    
    # Query to get video information from database
    query = """
    SELECT 
        v.video_id::text,
        v.video_path,
        v.title,
        COUNT(svx.screenshot_id) as screenshot_count
    FROM videos v
    LEFT JOIN screenshot_video_xref svx ON v.video_id = svx.video_id
    GROUP BY v.video_id, v.video_path, v.title
    ORDER BY v.video_path
    """
    
    print("🔍 Querying database for video information...")
    result = run_sql_query(query)
    
    if "error" in result:
        print(f"❌ Database error: {result['error']}")
        return
    
    if not result.get("rows"):
        print("❌ No video records found in database")
        return
    
    print(f"✅ Found {len(result['rows'])} video records\n")
    
    # Check each video path - show details for first 5, then summary
    working_videos = 0
    missing_videos = 0
    
    for i, row in enumerate(result["rows"], 1):
        video_id, db_video_path, title, screenshot_count = row
        
        # Show detailed info for first 5 videos
        if i <= 5:
            print(f"📹 Video {i}: {title or 'Untitled'}")
            print(f"   ID: {video_id}")
            print(f"   DB Path: {db_video_path}")
            print(f"   Screenshots: {screenshot_count}")
        
        # Test different path combinations
        test_paths = []
        
        if db_video_path:
            # Path as stored in DB
            test_paths.append(("Raw DB path", db_video_path))
            
            # With screenshots prefix
            screenshots_path = os.path.join("screenshots", db_video_path)
            test_paths.append(("With 'screenshots' prefix", screenshots_path))
            
            # With forward slashes
            forward_slash_path = db_video_path.replace("\\", "/")
            test_paths.append(("Forward slashes", forward_slash_path))
            
            # With screenshots + forward slashes
            screenshots_forward = os.path.join("screenshots", forward_slash_path)
            test_paths.append(("Screenshots + forward slashes", screenshots_forward))
        
        # Check which paths exist
        existing_paths = []
        for path_desc, path in test_paths:
            exists = os.path.exists(path)
            if i <= 5:  # Only show details for first 5
                status = "✅ EXISTS" if exists else "❌ NOT FOUND"
                print(f"   {status} {path_desc}: {path}")
            if exists:
                existing_paths.append(path)
        
        if existing_paths:
            working_videos += 1
            if i <= 5:
                print(f"   🎯 Working path(s): {len(existing_paths)} found")
        else:
            missing_videos += 1
            if i <= 5:
                print(f"   ⚠️  No working paths found!")
        
        if i <= 5:
            print()
    
    # Show summary for all videos
    if len(result['rows']) > 5:
        print(f"... and {len(result['rows']) - 5} more videos (details hidden)\n")
    
    print(f"📊 Video Path Summary:")
    print(f"   Total videos in database: {len(result['rows'])}")
    print(f"   Videos with working paths: {working_videos}")
    print(f"   Videos with missing files: {missing_videos}")
    print(f"   Success rate: {(working_videos/len(result['rows'])*100):.1f}%")
    print()
    
    # Also check what video files actually exist in the screenshots directory
    print("\n🗂️  Checking actual video files in screenshots directory...")
    
    screenshots_dir = "screenshots"
    if not os.path.exists(screenshots_dir):
        print(f"❌ Screenshots directory not found: {screenshots_dir}")
        return
    
    video_files = []
    for root, dirs, files in os.walk(screenshots_dir):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, screenshots_dir)
                video_files.append((full_path, rel_path))
    
    print(f"📁 Found {len(video_files)} video files in {screenshots_dir}:")
    for i, (full_path, rel_path) in enumerate(video_files[:10], 1):  # Show first 10
        file_size = os.path.getsize(full_path) / (1024*1024)  # MB
        print(f"   {i}. {rel_path} ({file_size:.1f} MB)")
    
    if len(video_files) > 10:
        print(f"   ... and {len(video_files) - 10} more")
    
    print(f"\n📊 Summary:")
    print(f"   Videos in database: {len(result['rows'])}")
    print(f"   Video files on disk: {len(video_files)}")

if __name__ == "__main__":
    test_video_paths() 