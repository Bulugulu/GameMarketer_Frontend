import json
import os
import re
from datetime import datetime
from typing import Dict, Tuple, Optional
import streamlit as st

def parse_agent_response(raw_response) -> Tuple[str, Optional[str]]:
    """
    Parse the agent response to extract user_response and developer_note.
    
    Args:
        raw_response: The response from the agent (can be dict, str, or other)
        
    Returns:
        Tuple[str, Optional[str]]: (user_response, developer_note)
    """
    if not raw_response:
        return "No response received", "Empty response from agent"
    
    # Method 1: Handle structured output (dictionary format)
    if isinstance(raw_response, dict):
        user_response = raw_response.get("user_reponse", raw_response.get("user_response", ""))
        developer_note = raw_response.get("developer_note", "")
        
        if not user_response:
            user_response = str(raw_response)  # Fallback to string representation
            developer_note = "Response was a dict but missing user_response field"
            
        return user_response, developer_note if developer_note else None
    
    # Method 2: Handle string input (legacy fallback)
    if not isinstance(raw_response, str):
        # Convert to string if it's some other type
        raw_response_str = str(raw_response)
        dev_note = f"Response was type {type(raw_response)}, converted to string"
        return raw_response_str, dev_note
    
    cleaned_response = raw_response.strip()
    
    # Method 3: Try direct JSON parsing
    try:
        parsed = json.loads(cleaned_response)
        # Extract user response and developer note (handle both spellings)
        user_response = parsed.get("user_reponse", parsed.get("user_response", ""))
        developer_note = parsed.get("developer_note", "")
        
        return user_response, developer_note if developer_note else None
        
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Method 4: Try to extract JSON from mixed content (e.g., markdown code blocks)
    json_patterns = [
        r'```json\s*(\{.*?\})\s*```',  # JSON in markdown code blocks
        r'```\s*(\{.*?\})\s*```',      # JSON in generic code blocks
        r'(\{[^{}]*"user_.*?"[^{}]*\})',  # Simple JSON pattern
        r'(\{.*?"user_.*?".*?\})',     # More flexible JSON pattern
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, cleaned_response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                user_response = parsed.get("user_reponse", parsed.get("user_response", ""))
                developer_note = parsed.get("developer_note", "")
                
                if user_response:  # Only return if we found a valid user response
                    return user_response, developer_note if developer_note else None
                    
            except (json.JSONDecodeError, AttributeError):
                continue
    
    # Method 5: Try to extract structured content using regex patterns
    # Look for patterns like 'user_response: "content"' or '"user_response": "content"'
    user_patterns = [
        r'"?user_reponse"?\s*:\s*"([^"]*)"',  # Handle the typo version
        r'"?user_response"?\s*:\s*"([^"]*)"',
        r'user_reponse\s*:\s*(.+?)(?:\n|$)',  # Without quotes
        r'user_response\s*:\s*(.+?)(?:\n|$)',
    ]
    
    dev_patterns = [
        r'"?developer_note"?\s*:\s*"([^"]*)"',
        r'developer_note\s*:\s*(.+?)(?:\n|$)',
    ]
    
    user_response = None
    developer_note = None
    
    for pattern in user_patterns:
        match = re.search(pattern, cleaned_response, re.IGNORECASE | re.DOTALL)
        if match:
            user_response = match.group(1).strip()
            break
    
    for pattern in dev_patterns:
        match = re.search(pattern, cleaned_response, re.IGNORECASE | re.DOTALL)
        if match:
            developer_note = match.group(1).strip()
            break
    
    if user_response:
        return user_response, developer_note if developer_note else None
    
    # Method 6: Check if the response looks like it might be attempting JSON format
    if '{' in cleaned_response and '}' in cleaned_response:
        # It looks like JSON but parsing failed
        dev_note = f"Response appears to be malformed JSON. Raw response: {cleaned_response[:200]}..."
        return cleaned_response, dev_note
    
    # Method 7: Fallback - treat entire response as user response
    # But create a developer note about the parsing failure
    fallback_dev_note = f"Unable to parse structured response. Expected structured format. Raw response type: {type(raw_response)}, length: {len(cleaned_response) if isinstance(cleaned_response, str) else 'unknown'}"
    
    # If the response is very short, include it in the dev note
    if isinstance(cleaned_response, str) and len(cleaned_response) < 100:
        fallback_dev_note += f", content: '{cleaned_response}'"
    
    return cleaned_response, fallback_dev_note

def log_developer_note(developer_note: str, user_query: str = "", conversation_id: str = "") -> None:
    """
    Log developer note to a JSON file.
    
    Args:
        developer_note (str): The developer note to log
        user_query (str): The original user query that generated this note
        conversation_id (str): Unique identifier for the conversation
    """
    if not developer_note:
        return
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Prepare log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "conversation_id": conversation_id or f"session_{hash(str(st.session_state.get('messages', [])))}",
        "user_query": user_query,
        "developer_note": developer_note,
        "message_count": len(st.session_state.get('messages', [])),
        "session_id": st.session_state.get('session_id', 'unknown')
    }
    
    # Define log file path
    log_file = os.path.join(logs_dir, "developer_notes.jsonl")
    
    try:
        # Append to JSONL file (one JSON object per line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        print(f"Developer note logged to {log_file}")
        
    except Exception as e:
        print(f"Failed to log developer note: {e}")

def get_recent_developer_notes(limit: int = 10) -> list:
    """
    Retrieve recent developer notes from the log file.
    
    Args:
        limit (int): Maximum number of notes to retrieve
        
    Returns:
        list: List of recent developer note entries
    """
    log_file = os.path.join("logs", "developer_notes.jsonl")
    
    if not os.path.exists(log_file):
        return []
    
    try:
        notes = []
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Get the last 'limit' lines
        for line in lines[-limit:]:
            if line.strip():
                notes.append(json.loads(line.strip()))
                
        return notes[::-1]  # Return in reverse order (most recent first)
        
    except Exception as e:
        print(f"Failed to read developer notes: {e}")
        return []

def display_developer_notes_panel():
    """
    Display a panel showing recent developer notes for debugging/development purposes.
    """
    with st.expander("🛠️ Developer Notes (Debug)", expanded=False):
        st.markdown("**Recent developer feedback and system insights:**")
        
        # Add clear button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Clear Logs", key="clear_dev_notes"):
                log_file = os.path.join("logs", "developer_notes.jsonl")
                if os.path.exists(log_file):
                    os.remove(log_file)
                    st.success("Developer notes cleared!")
                    st.rerun()
        
        notes = get_recent_developer_notes(limit=5)
        
        if not notes:
            st.markdown("*No developer notes yet.*")
            return
        
        for i, note in enumerate(notes):
            with st.container():
                timestamp = datetime.fromisoformat(note['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
                st.markdown(f"**{timestamp}** (Message #{note.get('message_count', 'N/A')})")
                
                if note.get('user_query'):
                    st.markdown(f"**User Query:** {note['user_query'][:100]}{'...' if len(note['user_query']) > 100 else ''}")
                
                st.markdown(f"**Developer Note:** {note['developer_note']}")
                
                if i < len(notes) - 1:
                    st.markdown("---") 