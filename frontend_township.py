import streamlit as st
from utils import (
    get_client, 
    get_agent_response, 
    display_screenshot_group, 
    show_fullscreen_image, 
    initialize_session_state,
    parse_agent_response,
    log_developer_note,
    display_developer_notes_panel,
    show_video_player
)
from utils.config import get_environment, get_chroma_config

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

def display_vector_debug_info():
    """Display vector similarity debug information"""
    if not st.session_state.vector_debug_info:
        return
    
    with st.expander("🔍 Vector Similarity Debug Info", expanded=False):
        # Add clear button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Recent Vector Search Results with Scores:**")
        with col2:
            if st.button("Clear Debug", key="clear_vector_debug"):
                st.session_state.vector_debug_info = []
                st.rerun()
        
        st.markdown("""
        **Score Interpretation:**
        
        **🆕 Cohere Relevance Scores (0.0-1.0) - Primary scoring when reranking is enabled:**
        - 🟢 **≥ 0.8**: Highly relevant (excellent semantic match)
        - 🟡 **0.6 - 0.79**: Moderately relevant (good semantic match)  
        - 🟠 **0.4 - 0.59**: Somewhat relevant (fair semantic match)
        - 🔴 **< 0.4**: Low relevance (poor semantic match)
        
        **📐 Cosine Distance (0.0-2.0) - Fallback when reranking unavailable:**
        - 🟢 **< 0.3**: Highly relevant (very similar semantic meaning)
        - 🟡 **0.3 - 0.7**: Moderately relevant (somewhat similar)  
        - 🟠 **0.7 - 1.2**: Somewhat relevant (loosely related)
        - 🔴 **> 1.2**: Low relevance (different semantic meaning)
        - **Formula**: `distance = 1 - cosine_similarity`
        - Distance range: 0.0 (identical) to 2.0 (opposite direction)
        """)
        
        for debug_info in reversed(st.session_state.vector_debug_info[-3:]):  # Show last 3 searches
            st.markdown(f"**Query:** `{debug_info['query']}`")
            st.markdown(f"**Content Type:** {debug_info['content_type']} | **Limit:** {debug_info['limit']}")
            
            # Check if we have reranking results or fallback distance results
            has_relevance_scores = False
            if debug_info.get('features') and debug_info['features']:
                has_relevance_scores = 'relevance_score' in debug_info['features'][0]
            elif debug_info.get('screenshots') and debug_info['screenshots']:
                has_relevance_scores = 'relevance_score' in debug_info['screenshots'][0]
            
            score_type = "Cohere Relevance" if has_relevance_scores else "Cosine Distance"
            st.markdown(f"**Scoring System:** {score_type}")
            
            if debug_info.get('features'):
                st.markdown("**Features Found:**")
                for i, feature in enumerate(debug_info['features'], 1):
                    if 'relevance_score' in feature:
                        # Cohere relevance score (higher is better)
                        score = feature['relevance_score']
                        relevance_color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🟠" if score >= 0.4 else "🔴"
                        st.markdown(f"  {relevance_color} `{score:.3f}` - {feature['name']} (ID: {feature['feature_id']})")
                    else:
                        # Cosine distance (lower is better)
                        distance = feature.get('distance', 0)
                        relevance_color = "🟢" if distance < 0.3 else "🟡" if distance < 0.7 else "🟠" if distance < 1.2 else "🔴"
                        st.markdown(f"  {relevance_color} `{distance:.4f}` - {feature['name']} (ID: {feature['feature_id']})")
            
            if debug_info.get('screenshots'):
                st.markdown("**Screenshots Found:**")
                for i, screenshot in enumerate(debug_info['screenshots'], 1):
                    caption_preview = screenshot['caption'][:40] + "..." if len(screenshot['caption']) > 40 else screenshot['caption']
                    
                    if 'relevance_score' in screenshot:
                        # Cohere relevance score (higher is better)
                        score = screenshot['relevance_score']
                        relevance_color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🟠" if score >= 0.4 else "🔴"
                        st.markdown(f"  {relevance_color} `{score:.3f}` - {caption_preview}")
                    else:
                        # Cosine distance (lower is better)
                        distance = screenshot.get('distance', 0)
                        relevance_color = "🟢" if distance < 0.3 else "🟡" if distance < 0.7 else "🟠" if distance < 1.2 else "🔴"
                        st.markdown(f"  {relevance_color} `{distance:.4f}` - {caption_preview}")
            
            if debug_info.get('distance_stats'):
                stats = debug_info['distance_stats']
                st.markdown(f"**Score Stats:** Min: `{stats['min']:.4f}` | Max: `{stats['max']:.4f}` | Avg: `{stats['avg']:.4f}`")
                if stats.get('suggested_cutoffs'):
                    cutoffs = stats['suggested_cutoffs']
                    st.markdown(f"**Suggested Cutoffs:** High relevance < `{cutoffs['high']:.4f}` | Medium relevance < `{cutoffs['medium']:.4f}`")
            
            st.markdown("---")

def main():
    st.title("Township Feature Analyst Chatbot (Agentic)")

    # Initialize session state
    initialize_session_state()

    # Initialize debug info storage if not exists
    if "vector_debug_info" not in st.session_state:
        st.session_state.vector_debug_info = []

    # Debug information (show only if environment detection might be wrong)
    current_env = get_environment()
    
    # Show debug info if we detect issues or if explicitly requested
    show_debug = st.sidebar.checkbox("🔧 Show Environment Debug", value=False)
    if show_debug:
        with st.sidebar.expander("🔍 Environment Debug Info", expanded=True):
            st.write(f"**Detected Environment:** {current_env}")
            
            # Show key Railway variables
            import os
            railway_indicators = [
                "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", 
                "RAILWAY_DEPLOYMENT_ID", "RAILWAY_ENVIRONMENT_ID"
            ]
            
            railway_detected = any(os.environ.get(var) for var in railway_indicators)
            st.write(f"**Railway Variables Present:** {'Yes' if railway_detected else 'No'}")
            
            for var in railway_indicators:
                value = os.environ.get(var)
                status = "✅" if value else "❌"
                display = value[:10] + "..." if value and len(value) > 10 else value or "Not set"
                st.write(f"{status} `{var}`: {display}")
            
            # ChromaDB config
            chroma_config = get_chroma_config()
            st.write(f"**ChromaDB Mode:** {'Railway HTTP' if chroma_config['is_railway'] else 'Local File'}")
            if chroma_config['host']:
                st.write(f"**ChromaDB Host:** {chroma_config['host'][:30]}...")
            
            # Quick fix option
            if current_env == "local" and railway_detected:
                st.warning("⚠️ Railway variables detected but environment is 'local'")
                if st.button("🔧 Force Railway Mode"):
                    os.environ["FORCE_RAILWAY_MODE"] = "true"
                    st.rerun()
            
            if os.environ.get("FORCE_RAILWAY_MODE"):
                st.info("🚂 Railway mode forced via FORCE_RAILWAY_MODE")
                if st.button("🔄 Clear Force Mode"):
                    if "FORCE_RAILWAY_MODE" in os.environ:
                        del os.environ["FORCE_RAILWAY_MODE"]
                    st.rerun()

    # Show fullscreen dialog if in fullscreen mode
    if st.session_state.fullscreen_mode:
        show_fullscreen_image()
    
    # Show video player dialog if in video player mode
    if st.session_state.get("video_player_mode", False):
        show_video_player()

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
            # Add user message immediately and trigger rerun to show it
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.waiting_for_response = True
            st.rerun()
        
        # Handle assistant response in a separate cycle
        if st.session_state.get("waiting_for_response", False):
            st.session_state.waiting_for_response = False
            
            client = get_client()
            if client:
                # Get the last user message for context
                last_user_message = st.session_state.messages[-1]["content"]
                current_conversation_history = [msg for msg in st.session_state.messages[:-1]]
                
                with st.spinner("Thinking..."):
                    raw_bot_response = get_agent_response(last_user_message, current_conversation_history)
                
                # Parse the response to extract user_response and developer_note
                user_response, developer_note = parse_agent_response(raw_bot_response)
                
                # Log developer note if present
                if developer_note:
                    log_developer_note(
                        developer_note=developer_note,
                        user_query=last_user_message,
                        conversation_id=f"session_{id(st.session_state)}"
                    )
                
                # Create the assistant message with only the user response
                assistant_message = {"role": "assistant", "content": user_response}
                
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
            # Display developer notes panel (for development/debugging)
            display_developer_notes_panel()
            
            # Display vector debug info
            display_vector_debug_info()
            
            # Screenshot preview drawer
            display_screenshot_drawer()

if __name__ == "__main__":
    main() 