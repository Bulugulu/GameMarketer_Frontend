import os
import streamlit as st

def is_r2_url(path):
    """Check if a path is an R2 presigned URL"""
    return path.startswith(('http://', 'https://')) and ('r2.cloudflarestorage.com' in path or 'r2.dev' in path)

@st.dialog("🎬 Video Player", width="large")
def show_video_player():
    """Video player dialog for watching videos at specific timestamps"""
    if not st.session_state.get("current_video_path") or not st.session_state.get("current_video_timestamp"):
        st.error("No video information available")
        return
    
    video_path = st.session_state.current_video_path
    timestamp = st.session_state.current_video_timestamp
    video_title = st.session_state.get("current_video_title", "Video")
    
    # Display video info
    st.markdown(f"**{video_title}**")
    st.markdown(f"Starting at: {format_timestamp(timestamp)}")
    
    # Check if this is an R2 URL or local path
    is_r2_video = is_r2_url(video_path)
    
    # Debug information
    with st.expander("🔧 Debug Info", expanded=False):
        st.markdown("**Path Information:**")
        st.markdown(f"- Video path: `{video_path}`")
        st.markdown(f"- Video type: {'R2 URL' if is_r2_video else 'Local file'}")
        st.markdown(f"- Video timestamp: {timestamp} seconds")
        
        if not is_r2_video:
            st.markdown(f"- File exists: {os.path.exists(video_path)}")
            st.markdown(f"- Current working directory: `{os.getcwd()}`")
            st.markdown(f"- Absolute path: `{os.path.abspath(video_path)}`")
            
            # Try different path combinations for local files
            if not os.path.exists(video_path):
                st.markdown("**Trying alternative paths:**")
                
                # Just the filename without screenshots prefix
                if video_path.startswith("screenshots"):
                    alt_path1 = video_path.replace("screenshots/", "").replace("screenshots\\", "")
                    st.markdown(f"- Without 'screenshots' prefix: `{alt_path1}` (exists: {os.path.exists(alt_path1)})")
                
                # With screenshots prefix if not already there
                if not video_path.startswith("screenshots"):
                    alt_path2 = os.path.join("screenshots", video_path)
                    st.markdown(f"- With 'screenshots' prefix: `{alt_path2}` (exists: {os.path.exists(alt_path2)})")
                
                # Try forward slashes
                alt_path3 = video_path.replace("\\", "/")
                st.markdown(f"- Forward slashes: `{alt_path3}` (exists: {os.path.exists(alt_path3)})")
                
                # Try backslashes
                alt_path4 = video_path.replace("/", "\\")
                st.markdown(f"- Backslashes: `{alt_path4}` (exists: {os.path.exists(alt_path4)})")
        else:
            st.markdown("- R2 URL: Served from Cloudflare R2")
    
    # Find the correct video path using centralized function
    working_path = find_video_file(video_path) if not is_r2_video else video_path
    
    # Display video or error
    if working_path:
        try:
            if is_r2_video:
                st.success(f"✅ Video served from R2: {video_title}")
            else:
                st.success(f"✅ Video found at: `{working_path}`")
            
            # Use Streamlit's video player with automatic timestamp seeking
            st.markdown(f"### 🎬 Video Player - {video_title}")
            
            # Convert timestamp to Streamlit-compatible format
            timestamp_str = f"{timestamp}s"  # Convert seconds to "123s" format
            
            try:
                if is_r2_video:
                    # For R2 URLs, use the URL directly
                    st.video(working_path, start_time=timestamp_str)
                    st.success(f"✅ **Auto-started at {format_timestamp(timestamp)}** - Video will begin at the screenshot timestamp")
                else:
                    # For local files, try loading as bytes first
                    with open(working_path, 'rb') as video_file:
                        video_bytes = video_file.read()
                    
                    st.video(video_bytes, start_time=timestamp_str)
                    st.success(f"✅ **Auto-started at {format_timestamp(timestamp)}** - Video will begin at the screenshot timestamp")
                
            except Exception as bytes_error:
                try:
                    # Fallback: Use file path directly (only for local files)
                    if not is_r2_video:
                        st.video(working_path, start_time=timestamp_str)
                        st.success(f"✅ **Auto-started at {format_timestamp(timestamp)}** - Video will begin at the screenshot timestamp")
                    else:
                        raise bytes_error  # Re-raise for R2 URLs
                        
                except Exception as path_error:
                    # Final fallback: Video without timestamp
                    st.video(working_path)
                    st.info(f"⏰ **Please manually seek to: {format_timestamp(timestamp)}** ({timestamp} seconds)")
                    st.warning("Auto-seek not available - seek manually using video controls")
            
            # Additional controls
            st.markdown("### 🎥 Additional Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if not is_r2_video and st.button("🖥️ Open in System Player", help="Open video file in default video player"):
                    try:
                        import subprocess
                        import platform
                        
                        system = platform.system().lower()
                        if system == "windows":
                            subprocess.run(f'start "" "{os.path.abspath(working_path)}"', shell=True)
                        elif system == "darwin":  # macOS
                            subprocess.run(["open", working_path])
                        else:  # Linux
                            subprocess.run(["xdg-open", working_path])
                            
                        st.success(f"Opening video externally. Seek to {format_timestamp(timestamp)} manually.")
                    except Exception as e:
                        st.error(f"Could not open video file: {e}")
                elif is_r2_video:
                    st.button("🖥️ Open in System Player", disabled=True, help="Not available for R2 URLs")
            
            with col2:
                if st.button("📋 Copy Info", help="Copy video and timestamp info"):
                    filename = os.path.basename(working_path) if not is_r2_video else video_title
                    info_text = f"Video: {filename}\nTimestamp: {format_timestamp(timestamp)} ({timestamp} seconds)\nSource: {'R2 Storage' if is_r2_video else 'Local file'}"
                    if not is_r2_video:
                        info_text += f"\nPath: {working_path}"
                    st.code(info_text, language=None)
                    st.success("Video info shown above")
            
            with col3:
                if st.button("🔄 Refresh Video", help="Reload the video player"):
                    st.rerun()
            
        except Exception as e:
            st.error(f"Error loading video: {e}")
            st.markdown("**Video File Information**")
            if is_r2_video:
                st.markdown(f"- R2 URL: `{working_path[:60]}...`")
            else:
                st.markdown(f"- Path: `{working_path}`")
            st.markdown(f"- Timestamp: {format_timestamp(timestamp)} ({timestamp} seconds)")
            
    else:
        st.error(f"❌ Video file not found")
        st.markdown("**Searched paths:**")
        st.markdown(f"- Primary: `{video_path}`")
        
        if not is_r2_video:
            # Show some attempted alternatives for debugging (only for local files)
            normalized_path = video_path.replace('\\', '/').replace('//', '/')
            st.markdown(f"- Normalized: `{normalized_path}`")
            
            if normalized_path.startswith("screenshots"):
                clean_path = normalized_path.replace("screenshots/", "")
                st.markdown(f"- Without prefix: `{clean_path}`")
            else:
                prefixed_path = os.path.join("screenshots", normalized_path)
                st.markdown(f"- With prefix: `{prefixed_path}`")
            
            st.markdown("**Please ensure the video file exists in one of these locations.**")
        else:
            st.markdown("**R2 URL may have expired or be invalid.**")
        
        # Manual timestamp info
        st.info(f"**Timestamp:** {format_timestamp(timestamp)} ({timestamp} seconds)")
    
    # Close button
    if st.button("Close Video Player", type="primary", use_container_width=True):
        # Clear video session state
        for key in ["current_video_path", "current_video_timestamp", "current_video_title"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.video_player_mode = False
        st.rerun()

def format_timestamp(seconds):
    """Convert seconds to MM:SS or HH:MM:SS format"""
    if seconds is None:
        return "00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def display_screenshot_group(screenshot_group, unique_key_prefix=""):
    """Helper function to display a screenshot group with clickable thumbnails and video buttons"""
    group_title = screenshot_group.get("group_title", "Retrieved Screenshots")
    game_name = screenshot_group.get("game_name")  # Get game name for subtitle
    image_paths_for_grid = screenshot_group.get("image_paths", [])
    group_type = screenshot_group.get("group_type", "screen")  # New field to identify feature groups
    screenshot_data = screenshot_group.get("screenshot_data", [])  # Enhanced data with video info
    serving_mode = screenshot_group.get("serving_mode", "local")  # Add serving mode info
    
    # Display feature name as main title
    st.write(f"**{group_title}**")
    
    # Display game name as subtitle if available
    if game_name and game_name != "Unknown Game":
        st.caption(f"🎮 {game_name}")
    
    # Show serving mode indicator
    if serving_mode == "r2":
        st.caption("📡 Served from Cloudflare R2")
    else:
        st.caption("📁 Served from local filesystem")
    
    if not image_paths_for_grid:
        st.write("(No images found for this group)")
        return

    # For feature groups, show single fullscreen button at the top
    if group_type == "feature" and image_paths_for_grid:
        button_key = f"{unique_key_prefix}_feature_fullscreen_{hash(group_title)}"
        if st.button("🔍 View Feature Screenshots", key=f"{button_key}_btn"):
            st.session_state.fullscreen_mode = True
            st.session_state.current_fullscreen_images = image_paths_for_grid
            st.session_state.current_image_index = 0
            st.session_state.current_group_title = group_title
            st.session_state.current_game_name = game_name  # Store game name for fullscreen display
            # Store screenshot data for video access in fullscreen mode
            st.session_state.current_screenshot_data = screenshot_data
            st.rerun()
    
    # Display screenshots in grid
    num_columns = 3
    cols = st.columns(num_columns)
    
    for index, img_path in enumerate(image_paths_for_grid):
        col_index = index % num_columns
        with cols[col_index]:
            # Check if this is an R2 URL or local path
            is_r2_image = is_r2_url(img_path)
            
            # For R2 URLs, we don't need to check file existence
            # For local paths, we still check if the file exists
            path_exists = True if is_r2_image else os.path.exists(img_path)
            
            if path_exists:
                try:
                    # For legacy/screen groups, still show individual buttons
                    if group_type != "feature":
                        # Create a unique key for each image button
                        button_key = f"{unique_key_prefix}_img_{index}_{hash(img_path)}"
                        
                        # Display thumbnail image with click handler
                        if st.button("🔍 View Fullscreen", key=f"{button_key}_btn"):
                            st.session_state.fullscreen_mode = True
                            st.session_state.current_fullscreen_images = image_paths_for_grid
                            st.session_state.current_image_index = index
                            st.session_state.current_group_title = group_title
                            st.session_state.current_game_name = game_name  # Store game name for fullscreen display
                            st.session_state.current_screenshot_data = screenshot_data
                            st.rerun()
                    
                    # Show thumbnail - Streamlit handles both local paths and URLs
                    st.image(img_path, width=300)
                    
                    # Add "watch in video" button if video info is available
                    if index < len(screenshot_data):
                        screenshot_info = screenshot_data[index]
                        video_info = screenshot_info.get("video_info")
                        
                        if video_info and video_info.get("video_path") and video_info.get("video_timestamp_seconds") is not None:
                            video_button_key = f"{unique_key_prefix}_video_{index}_{hash(img_path)}"
                            timestamp = video_info["video_timestamp_seconds"]
                            video_title = video_info.get("video_title", "Video")
                            
                            if st.button(f"🎬 Watch in Video ({format_timestamp(timestamp)})", 
                                       key=f"{video_button_key}_btn",
                                       help=f"Watch {video_title} at {format_timestamp(timestamp)}"):
                                # Store video info in session state
                                st.session_state.current_video_path = video_info["video_path"]
                                st.session_state.current_video_timestamp = timestamp
                                st.session_state.current_video_title = video_title
                                st.session_state.video_player_mode = True
                                st.rerun()
                        else:
                            # Show disabled button or message if no video available
                            st.markdown("*No video available for this screenshot*")
                    
                except Exception as e:
                    st.error(f"Error displaying image: {e}")
                    st.write(f"Path: {img_path[:60]}{'...' if len(img_path) > 60 else ''}")
            else:
                # Only show warning for local paths (R2 URLs are handled above)
                st.warning(f"Missing: {os.path.basename(img_path)}")

@st.dialog(" ", width="large")  # Empty title to remove "Image Viewer"
def show_fullscreen_image():
    """Fullscreen image viewer dialog with video functionality"""
    if not st.session_state.current_fullscreen_images:
        st.error("No images to display")
        return
    
    current_index = st.session_state.current_image_index
    images = st.session_state.current_fullscreen_images
    screenshot_data = st.session_state.get("current_screenshot_data", [])
    
    # Display current image info
    st.markdown(f"**{st.session_state.current_group_title}**")
    
    # Display game name if available
    current_game_name = st.session_state.get("current_game_name")
    if current_game_name and current_game_name != "Unknown Game":
        st.caption(f"🎮 {current_game_name}")
    
    st.markdown(f"Image {current_index + 1} of {len(images)}")
    
    # Show video button for current image if available
    if current_index < len(screenshot_data):
        current_screenshot = screenshot_data[current_index]
        video_info = current_screenshot.get("video_info")
        
        if video_info and video_info.get("video_path") and video_info.get("video_timestamp_seconds") is not None:
            timestamp = video_info["video_timestamp_seconds"]
            video_title = video_info.get("video_title", "Video")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"🎬 Watch in Video", 
                           key="fullscreen_video_btn",
                           help=f"Watch {video_title} at {format_timestamp(timestamp)}"):
                    # Store video info in session state
                    st.session_state.current_video_path = video_info["video_path"]
                    st.session_state.current_video_timestamp = timestamp
                    st.session_state.current_video_title = video_title
                    st.session_state.video_player_mode = True
                    st.session_state.fullscreen_mode = False  # Close fullscreen to show video
                    st.rerun()
    
    # Layout with navigation buttons on sides of the image
    col1, col2, col3 = st.columns([1, 8, 1])
    
    # Left navigation button
    with col1:
        st.write("")  # Add some vertical space
        st.write("")
        if st.button("◀", disabled=(current_index == 0), key="prev_btn", 
                    help="Previous image"):
            st.session_state.current_image_index = max(0, current_index - 1)
            st.rerun()
    
    # Display the current image in the center
    with col2:
        current_image_path = images[current_index]
        is_r2_image = is_r2_url(current_image_path)
        
        # For R2 URLs, we don't need to check file existence
        # For local paths, we still check if the file exists
        path_exists = True if is_r2_image else os.path.exists(current_image_path)
        
        if path_exists:
            try:
                # Streamlit handles both local paths and URLs
                st.image(current_image_path, use_container_width=True)
                
                # Show serving info
                if is_r2_image:
                    st.caption("📡 Served from Cloudflare R2")
                else:
                    st.caption("📁 Local file")
                    
            except Exception as e:
                st.error(f"Error displaying image: {e}")
                st.write(f"Path: {current_image_path[:80]}{'...' if len(current_image_path) > 80 else ''}")
        else:
            st.error(f"Image not found: {os.path.basename(current_image_path)}")
    
    # Right navigation button
    with col3:
        st.write("")  # Add some vertical space
        st.write("")
        if st.button("▶", disabled=(current_index == len(images) - 1), key="next_btn",
                    help="Next image"):
            st.session_state.current_image_index = min(len(images) - 1, current_index + 1)
            st.rerun()
    
    # Close button at the bottom
    st.write("")  # Add some space
    if st.button("Close", type="primary", use_container_width=True):
        st.session_state.fullscreen_mode = False
        st.rerun()

def initialize_session_state():
    """Initialize session state variables for the UI"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "screenshots_to_display" not in st.session_state:
        st.session_state.screenshots_to_display = []
    if "fullscreen_mode" not in st.session_state:
        st.session_state.fullscreen_mode = False
    if "current_fullscreen_images" not in st.session_state:
        st.session_state.current_fullscreen_images = []
    if "current_image_index" not in st.session_state:
        st.session_state.current_image_index = 0
    if "current_group_title" not in st.session_state:
        st.session_state.current_group_title = ""
    if "current_game_name" not in st.session_state:
        st.session_state.current_game_name = ""
    if "waiting_for_response" not in st.session_state:
        st.session_state.waiting_for_response = False
    # Video player state
    if "video_player_mode" not in st.session_state:
        st.session_state.video_player_mode = False
    if "current_screenshot_data" not in st.session_state:
        st.session_state.current_screenshot_data = []

def find_video_file(video_path):
    """Find the actual video file, trying multiple path combinations and extensions"""
    if not video_path:
        return None
    
    # If it's an R2 URL, return as-is
    if is_r2_url(video_path):
        return video_path
    
    # Normalize path separators to avoid mixed separators
    video_path = video_path.replace('\\', '/').replace('//', '/')
    
    alternatives = []
    
    # Try the path as-is first (normalized)
    alternatives.append(os.path.normpath(video_path))
    
    # Try without screenshots prefix if it exists
    if video_path.startswith("screenshots"):
        clean_path = video_path.replace("screenshots/", "")
        alternatives.append(os.path.normpath(clean_path))
    
    # Try with screenshots prefix if it doesn't exist
    if not video_path.startswith("screenshots"):
        prefixed_path = os.path.normpath(os.path.join("screenshots", video_path))
        alternatives.append(prefixed_path)
    
    # Common video extensions to try
    extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    
    # Create copies with different extensions
    base_alternatives = alternatives[:]
    for base_path in base_alternatives:
        path_without_ext = os.path.splitext(base_path)[0]
        for ext in extensions:
            alternatives.append(path_without_ext + ext)
    
    # Check each alternative
    for alt_path in alternatives:
        if os.path.exists(alt_path):
            return alt_path
    
    return None 