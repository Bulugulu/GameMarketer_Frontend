import os
import streamlit as st

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
    
    # Debug information
    with st.expander("🔧 Debug Info", expanded=False):
        st.markdown("**Path Information:**")
        st.markdown(f"- Raw video path: `{video_path}`")
        st.markdown(f"- File exists: {os.path.exists(video_path)}")
        st.markdown(f"- Current working directory: `{os.getcwd()}`")
        st.markdown(f"- Absolute path: `{os.path.abspath(video_path)}`")
        
        # Try different path combinations
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
    
    # Find the correct video path using centralized function
    working_path = find_video_file(video_path)
    
    # Display video or error
    if working_path:
        try:
            st.success(f"✅ Video found at: `{working_path}`")
            
            # Use Streamlit's video player with automatic timestamp seeking
            st.markdown(f"### 🎬 Video Player - {video_title}")
            
            # Convert timestamp to Streamlit-compatible format
            timestamp_str = f"{timestamp}s"  # Convert seconds to "123s" format
            
            try:
                # First try: Load video bytes and serve through Streamlit
                with open(working_path, 'rb') as video_file:
                    video_bytes = video_file.read()
                
                st.video(video_bytes, start_time=timestamp_str)
                st.success(f"✅ **Auto-started at {format_timestamp(timestamp)}** - Video will begin at the screenshot timestamp")
                
            except Exception as bytes_error:
                try:
                    # Fallback: Use file path directly
                    st.video(working_path, start_time=timestamp_str)
                    st.success(f"✅ **Auto-started at {format_timestamp(timestamp)}** - Video will begin at the screenshot timestamp")
                    
                except Exception as path_error:
                    # Final fallback: Video without timestamp
                    st.video(working_path)
                    st.info(f"⏰ **Please manually seek to: {format_timestamp(timestamp)}** ({timestamp} seconds)")
                    st.warning("Auto-seek not available - seek manually using video controls")
            
            # Additional controls
            st.markdown("### 🎥 Additional Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🖥️ Open in System Player", help="Open video file in default video player"):
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
            
            with col2:
                if st.button("📋 Copy Info", help="Copy video and timestamp info"):
                    info_text = f"Video: {os.path.basename(working_path)}\nTimestamp: {format_timestamp(timestamp)} ({timestamp} seconds)\nPath: {working_path}"
                    st.code(info_text, language=None)
                    st.success("Video info shown above")
            
            with col3:
                if st.button("🔄 Refresh Video", help="Reload the video player"):
                    st.rerun()
            
        except Exception as e:
            st.error(f"Error loading video: {e}")
            st.markdown("**Video File Information**")
            st.markdown(f"- Path: `{working_path}`")
            st.markdown(f"- Timestamp: {format_timestamp(timestamp)} ({timestamp} seconds)")
            
    else:
        st.error(f"❌ Video file not found")
        st.markdown("**Searched paths:**")
        st.markdown(f"- Primary: `{video_path}`")
        
        # Show some attempted alternatives for debugging
        normalized_path = video_path.replace('\\', '/').replace('//', '/')
        st.markdown(f"- Normalized: `{normalized_path}`")
        
        if normalized_path.startswith("screenshots"):
            clean_path = normalized_path.replace("screenshots/", "")
            st.markdown(f"- Without prefix: `{clean_path}`")
        else:
            prefixed_path = os.path.join("screenshots", normalized_path)
            st.markdown(f"- With prefix: `{prefixed_path}`")
        
        st.markdown("**Please ensure the video file exists in one of these locations.**")
        
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
    image_paths_for_grid = screenshot_group.get("image_paths", [])
    group_type = screenshot_group.get("group_type", "screen")  # New field to identify feature groups
    screenshot_data = screenshot_group.get("screenshot_data", [])  # Enhanced data with video info
    
    st.write(f"**{group_title}**")
    
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
            # Store screenshot data for video access in fullscreen mode
            st.session_state.current_screenshot_data = screenshot_data
            st.rerun()
    
    # Display screenshots in grid
    num_columns = 3
    cols = st.columns(num_columns)
    
    for index, img_path in enumerate(image_paths_for_grid):
        col_index = index % num_columns
        with cols[col_index]:
            if os.path.exists(img_path):
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
                            st.session_state.current_screenshot_data = screenshot_data
                            st.rerun()
                    
                    # Show thumbnail
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
                    st.error(f"Error displaying image {img_path}: {e}")
            else:
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
        if os.path.exists(current_image_path):
            try:
                st.image(current_image_path, use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying image: {e}")
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