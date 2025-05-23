import streamlit as st
from utils import (
    get_client, 
    get_agent_response, 
    display_screenshot_group, 
    show_fullscreen_image, 
    initialize_session_state
)

def main():
    st.title("Township Feature Analyst Chatbot (Agentic)")

    # Initialize session state
    initialize_session_state()

    # Show fullscreen dialog if in fullscreen mode
    if st.session_state.fullscreen_mode:
        show_fullscreen_image()

    # Display chat messages
    for msg_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str):
                st.markdown(message["content"])
            else:
                st.markdown(str(message["content"]))
            
            # Display screenshots if they exist in this message
            if "screenshots" in message:
                st.markdown("**Related Screenshots:**")
                for group_index, screenshot_group in enumerate(message["screenshots"]):
                    unique_key = f"msg_{msg_index}_group_{group_index}"
                    display_screenshot_group(screenshot_group, unique_key)

    # Handle new user input
    if prompt := st.chat_input("Ask about Township features or screens..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)

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
            
            with st.chat_message("assistant"): 
                st.markdown(bot_response_content)
                
                # Display screenshots immediately if they exist
                if "screenshots" in assistant_message:
                    st.markdown("**Related Screenshots:**")
                    for group_index, screenshot_group in enumerate(assistant_message["screenshots"]):
                        unique_key = f"new_msg_group_{group_index}"
                        display_screenshot_group(screenshot_group, unique_key)
        else:
            error_message = "OpenAI client not initialized. Please check your API key."
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"): 
                st.markdown(error_message)

if __name__ == "__main__":
    main() 