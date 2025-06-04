"""
Context detection utility for handling both Streamlit and non-Streamlit execution environments.
This allows tools to work seamlessly in both frontend (Streamlit) and backend (evaluation) contexts.
"""

import streamlit as st
from typing import Any, Dict, List


class ExecutionContext:
    """Utility class to detect and handle different execution contexts."""
    
    # Class-level storage for non-Streamlit contexts
    _mock_session_state = {}
    
    @staticmethod
    def is_streamlit_available() -> bool:
        """Check if we're running in a Streamlit context."""
        try:
            # Try to access session state - this will fail outside Streamlit
            _ = st.session_state
            # Also check for script run context 
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            return get_script_run_ctx() is not None
        except Exception:
            return False
    
    @staticmethod
    def get_session_state() -> Dict[str, Any]:
        """Get session state that works in both Streamlit and non-Streamlit contexts."""
        if ExecutionContext.is_streamlit_available():
            return st.session_state
        else:
            # Return mock session state for non-Streamlit contexts
            return ExecutionContext._mock_session_state
    
    @staticmethod
    def should_display_ui() -> bool:
        """Check if we should perform UI display operations."""
        return ExecutionContext.is_streamlit_available()
    
    @staticmethod
    def safe_ui_operation(ui_func, *args, **kwargs):
        """Safely execute a UI operation only in Streamlit context."""
        if ExecutionContext.should_display_ui():
            try:
                return ui_func(*args, **kwargs)
            except Exception as e:
                print(f"[DEBUG] UI operation failed: {e}")
                return None
        else:
            # In non-UI context, just log the operation
            print(f"[DEBUG] UI operation skipped (non-Streamlit context): {ui_func.__name__}")
            return None
    
    @staticmethod
    def initialize_session_state_key(key: str, default_value: Any = None):
        """Initialize a session state key if it doesn't exist, works in both contexts."""
        session_state = ExecutionContext.get_session_state()
        if key not in session_state:
            session_state[key] = default_value if default_value is not None else []
    
    @staticmethod
    def get_session_state_value(key: str, default: Any = None) -> Any:
        """Get a session state value safely."""
        session_state = ExecutionContext.get_session_state()
        return session_state.get(key, default)
    
    @staticmethod
    def set_session_state_value(key: str, value: Any):
        """Set a session state value safely."""
        session_state = ExecutionContext.get_session_state()
        session_state[key] = value
    
    @staticmethod
    def append_to_session_list(key: str, value: Any, max_length: int = None):
        """Append to a session state list, maintaining max length."""
        ExecutionContext.initialize_session_state_key(key, [])
        session_state = ExecutionContext.get_session_state()
        
        if not isinstance(session_state[key], list):
            session_state[key] = []
        
        session_state[key].append(value)
        
        # Maintain max length if specified
        if max_length and len(session_state[key]) > max_length:
            session_state[key] = session_state[key][-max_length:]


class StreamlitSafeLogger:
    """Logger that works safely in both Streamlit and non-Streamlit contexts."""
    
    @staticmethod
    def info(message: str):
        if ExecutionContext.should_display_ui():
            st.info(message)
        else:
            print(f"[INFO] {message}")
    
    @staticmethod
    def warning(message: str):
        if ExecutionContext.should_display_ui():
            st.warning(message)
        else:
            print(f"[WARNING] {message}")
    
    @staticmethod
    def error(message: str):
        if ExecutionContext.should_display_ui():
            st.error(message)
        else:
            print(f"[ERROR] {message}")
    
    @staticmethod
    def success(message: str):
        if ExecutionContext.should_display_ui():
            st.success(message)
        else:
            print(f"[SUCCESS] {message}")
    
    @staticmethod
    def debug(message: str):
        print(f"[DEBUG] {message}")


# Convenience instances
logger = StreamlitSafeLogger()
context = ExecutionContext() 