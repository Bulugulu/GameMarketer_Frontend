import streamlit as st
from utils import (
    get_client, 
    get_agent_response, 
    display_screenshot_group, 
    show_fullscreen_image, 
    initialize_session_state
)

# Configure page to use wide layout
st.set_page_config(
    page_title="Township Feature Analyst",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Custom CSS to maximize space usage
st.markdown("""
<style>
    /* Prevent page scrolling */
    html, body {
        overflow: hidden !important;
        height: 100vh !important;
        margin: 0 !important;
    }
    
    /* Main app container */
    .stApp {
        overflow: hidden !important;
        height: 100vh !important;
    }
    
    /* Base layout */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
        height: calc(100vh - 60px);
        overflow: hidden !important;
    }
    
    /* Column container to prevent scrolling */
    [data-testid="stHorizontalBlock"] {
        overflow: hidden !important;
        height: 100% !important;
    }
    
    /* Chat container specific height (400px) */
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 400px"] {
        overflow-y: auto !important;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.5rem;
        background-color: #fafafa;
    }
    
    /* Screenshot container specific height (700px) */
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 700px"] {
        overflow-y: auto !important;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        background-color: #f8f9fa;
    }
    
    /* Ensure both columns stay within viewport */
    [data-testid="column"] {
        height: calc(100vh - 100px) !important;
        max-height: calc(100vh - 100px) !important;
    }
    
    /* Ensure chat messages are properly spaced */
    .stChatMessage {
        margin-bottom: 0.5rem;
    }
    
    /* Carousel container should not cause overflow */
    .carousel-container {
        width: 100%;
        overflow-x: hidden;
    }
    
    /* Hide scrollbar for cleaner look but keep functionality */
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 700px"]::-webkit-scrollbar {
        width: 6px;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 700px"]::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 700px"]::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 3px;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"][style*="height: 700px"]::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
</style>
""", unsafe_allow_html=True)

def display_screenshot_drawer():
    """Display all screenshots from current conversation in organized groups"""
    # Collect all screenshots from conversation
    all_screenshots = []
    for message in st.session_state.messages:
        if message["role"] == "assistant" and "screenshots" in message:
            all_screenshots.extend(message["screenshots"])
    
    if not all_screenshots:
        st.markdown("*No screenshots yet. Ask a question to see feature screenshots here.*")
        return
    
    st.markdown("### 📸 Feature Screenshots")
    
    # Group screenshots by feature to avoid duplicates
    feature_groups = {}
    for screenshot_group in all_screenshots:
        group_title = screenshot_group.get("group_title", "Unknown")
        if group_title not in feature_groups:
            feature_groups[group_title] = screenshot_group
        else:
            # Merge image paths if we have multiple groups with same title
            existing_paths = set(feature_groups[group_title]["image_paths"])
            new_paths = screenshot_group.get("image_paths", [])
            for path in new_paths:
                if path not in existing_paths:
                    feature_groups[group_title]["image_paths"].append(path)
    
    # Display each feature group
    for idx, (feature_name, screenshot_group) in enumerate(feature_groups.items()):
        unique_key = f"drawer_group_{idx}"
        display_screenshot_group(screenshot_group, unique_key)

def main():
    st.title("Township Feature Analyst Chatbot (Agentic)")

    # Initialize session state
    initialize_session_state()

    # Show fullscreen dialog if in fullscreen mode
    if st.session_state.fullscreen_mode:
        show_fullscreen_image()

    # Create main layout: chat on left (30%), screenshot drawer on right (70%)
    chat_col, screenshot_col = st.columns([3, 7], gap="medium")  # Added gap parameter for better spacing
    
    with chat_col:
        st.markdown("### 💬 Chat")
        
        # Create a container with a conservative height to ensure input is visible
        # Using 400px to leave plenty of room for header and input
        chat_container = st.container(height=400)
        
        with chat_container:
            # Display chat messages (without screenshots)
            for msg_index, message in enumerate(st.session_state.messages):
                with st.chat_message(message["role"]):
                    # Only display the text content, no screenshots
                    if isinstance(message["content"], str):
                        st.markdown(message["content"])
                    else:
                        st.markdown(str(message["content"]))

        # Add a small spacer to ensure separation
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Handle new user input - this stays at the bottom
        if prompt := st.chat_input("Ask about Township features...", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            client = get_client()
            if client:
                current_conversation_history = [msg for msg in st.session_state.messages[:-1]]
                bot_response_content = get_agent_response(prompt, current_conversation_history)
                
                # Create the assistant message
                assistant_message = {"role": "assistant", "content": bot_response_content}
                
                # If screenshots were generated, add them to the message
                if st.session_state.screenshots_to_display:
                    assistant_message["screenshots"] = st.session_state.screenshots_to_display.copy()
                    st.session_state.screenshots_to_display = []  # Clear for next use
                
                st.session_state.messages.append(assistant_message)
                
                # Trigger rerun to update everything
                st.rerun()
            else:
                error_message = "OpenAI client not initialized. Please check your API key."
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                st.rerun()
    
    with screenshot_col:
        # Create a scrollable container for the screenshot drawer
        screenshot_container = st.container(height=700)  # Fixed height container with scrolling
        
        with screenshot_container:
            # Screenshot preview drawer
            display_screenshot_drawer()

if __name__ == "__main__":
    main() 