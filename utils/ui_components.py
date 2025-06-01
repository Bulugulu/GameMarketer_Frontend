import os
import streamlit as st

def display_screenshot_group(screenshot_group, unique_key_prefix=""):
    """Helper function to display a screenshot group with clickable thumbnails"""
    group_title = screenshot_group.get("group_title", "Retrieved Screenshots")
    image_paths_for_grid = screenshot_group.get("image_paths", [])
    group_type = screenshot_group.get("group_type", "screen")  # New field to identify feature groups
    
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
                            st.rerun()
                    
                    # Show thumbnail
                    st.image(img_path, width=300)
                except Exception as e:
                    st.error(f"Error displaying image {img_path}: {e}")
            else:
                st.warning(f"Missing: {os.path.basename(img_path)}")

@st.dialog(" ", width="large")  # Empty title to remove "Image Viewer"
def show_fullscreen_image():
    """Fullscreen image viewer dialog"""
    if not st.session_state.current_fullscreen_images:
        st.error("No images to display")
        return
    
    current_index = st.session_state.current_image_index
    images = st.session_state.current_fullscreen_images
    
    # Display current image info
    st.markdown(f"**{st.session_state.current_group_title}**")
    st.markdown(f"Image {current_index + 1} of {len(images)}")
    
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