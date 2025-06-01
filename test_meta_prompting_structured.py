#!/usr/bin/env python3
"""
Test script for the improved meta prompting functionality with structured output
"""

import json
import os
import sys
from datetime import datetime

# Add the current directory to the path to import utils
sys.path.append('.')

from utils.meta_prompting import parse_agent_response, log_developer_note, get_recent_developer_notes

def test_structured_response_parsing():
    """Test the new structured response parsing functionality"""
    print("Testing structured response parsing...")
    
    # Test case 1: Dictionary format (new structured output)
    dict_response = {
        "user_reponse": "This is the user response",
        "developer_note": "This is a developer note"
    }
    user_response, dev_note = parse_agent_response(dict_response)
    assert user_response == "This is the user response"
    assert dev_note == "This is a developer note"
    print("✓ Dictionary format parsing works correctly")
    
    # Test case 2: Dictionary with corrected spelling
    corrected_dict = {
        "user_response": "Another user response", 
        "developer_note": "Another developer note"
    }
    user_response, dev_note = parse_agent_response(corrected_dict)
    assert user_response == "Another user response"
    assert dev_note == "Another developer note"
    print("✓ Dictionary with corrected spelling works")
    
    # Test case 3: Dictionary with empty developer note
    empty_dev_dict = {
        "user_reponse": "Response with no dev note",
        "developer_note": ""
    }
    user_response, dev_note = parse_agent_response(empty_dev_dict)
    assert user_response == "Response with no dev note"
    assert dev_note is None
    print("✓ Empty developer note handling works")
    
    # Test case 4: Dictionary missing user_response field
    malformed_dict = {
        "response": "This is wrong field name",
        "developer_note": "Missing user_response field"
    }
    user_response, dev_note = parse_agent_response(malformed_dict)
    assert "response" in user_response  # Should fallback to string representation
    assert "missing user_response field" in dev_note.lower()
    print("✓ Malformed dictionary fallback works")
    
    # Test case 5: Non-string, non-dict input
    weird_input = ["this", "is", "a", "list"]
    user_response, dev_note = parse_agent_response(weird_input)
    assert "list" in user_response.lower()
    assert "type" in dev_note.lower()
    print("✓ Non-string/non-dict input handling works")
    
    print("All structured parsing tests passed!\n")

def test_backwards_compatibility():
    """Test that legacy JSON string parsing still works"""
    print("Testing backwards compatibility...")
    
    # Test case 1: Valid JSON string (legacy format)
    json_string = '{"user_reponse": "Legacy JSON response", "developer_note": "Legacy dev note"}'
    user_response, dev_note = parse_agent_response(json_string)
    assert user_response == "Legacy JSON response"
    assert dev_note == "Legacy dev note"
    print("✓ Legacy JSON string parsing works")
    
    # Test case 2: Plain text (fallback)
    plain_text = "This is just plain text response."
    user_response, dev_note = parse_agent_response(plain_text)
    assert user_response == plain_text
    assert "unable to parse" in dev_note.lower()
    print("✓ Plain text fallback works")
    
    print("All backwards compatibility tests passed!\n")

def test_end_to_end_structured():
    """Test the complete workflow with structured output"""
    print("Testing end-to-end structured workflow...")
    
    # Clear any existing logs for clean test
    log_file = os.path.join("logs", "developer_notes.jsonl")
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # Simulate structured agent response
    structured_response = {
        "user_reponse": "Township has comprehensive farming mechanics including crop planting, harvesting, and animal care systems.",
        "developer_note": "User asked about farming features. Response covers basic mechanics but could include more details about crop rotation and seasonal events."
    }
    
    # Parse the response
    user_response, dev_note = parse_agent_response(structured_response)
    
    # Log the developer note
    if dev_note:
        log_developer_note(
            developer_note=dev_note,
            user_query="What farming features does Township have?",
            conversation_id="structured_test_session"
        )
    
    # Verify the workflow
    assert user_response == "Township has comprehensive farming mechanics including crop planting, harvesting, and animal care systems."
    
    notes = get_recent_developer_notes(limit=1)
    latest_note = notes[0]
    assert "farming features" in latest_note["developer_note"]
    assert latest_note["user_query"] == "What farming features does Township have?"
    
    print("✓ End-to-end structured workflow works correctly")
    print(f"  User sees: {user_response}")
    print(f"  Developer note logged: {dev_note[:50]}...")
    
    print("All structured tests completed successfully! 🎉")

if __name__ == "__main__":
    print("Meta Prompting Structured Output Test Suite")
    print("=" * 50)
    
    try:
        test_structured_response_parsing()
        test_backwards_compatibility()
        test_end_to_end_structured()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    
    print("\n✅ All tests passed! Structured meta prompting is working correctly.") 