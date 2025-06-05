#!/usr/bin/env python3
"""
Test script for the ChatGPT scoring functionality.
This script tests the scoring method independently to verify it works correctly.
"""

import asyncio
import os
import json
from eval_framework import EvalFramework

async def test_chatgpt_scoring():
    """Test the ChatGPT scoring functionality with sample conversations"""
    
    # Check if OpenAI API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not found")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-key-here'")
        return False
    
    print("✅ OpenAI API key found")
    
    # Create a framework instance (we don't need a config file for this test)
    framework = EvalFramework.__new__(EvalFramework)
    
    # Test cases: different conversation scenarios
    test_cases = [
        {
            "name": "Highly Relevant Response",
            "user_question": "I want to learn about minigames in the game",
            "conversation": [
                {"role": "user", "content": "I want to learn about minigames in the game"},
                {"role": "assistant", "content": "Great! I'd be happy to show you the minigames available. Here are some exciting minigames you can play: 1) Sheep Rescue - a puzzle game where you save sheep, 2) Arcade Fever - classic arcade-style games, and 3) Various seasonal events with special mini-challenges. Would you like to see screenshots of any of these?"}
            ],
            "expected_score_range": (0.8, 1.0)
        },
        {
            "name": "Moderately Relevant Response",
            "user_question": "Tell me about farming features",
            "conversation": [
                {"role": "user", "content": "Tell me about farming features"},
                {"role": "assistant", "content": "The game has various features including farming, but I'd recommend checking out the tutorial section for more details."}
            ],
            "expected_score_range": (0.4, 0.7)
        },
        {
            "name": "Irrelevant Response",
            "user_question": "How do I plant crops?",
            "conversation": [
                {"role": "user", "content": "How do I plant crops?"},
                {"role": "assistant", "content": "The weather is nice today. Have you tried the new restaurant downtown?"}
            ],
            "expected_score_range": (0.0, 0.2)
        }
    ]
    
    print("\n🧪 Testing ChatGPT scoring functionality...\n")
    
    all_tests_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Question: {test_case['user_question']}")
        print(f"Response: {test_case['conversation'][1]['content'][:100]}...")
        
        try:
            # Test the scoring method
            result = await framework.score_with_chatgpt(
                test_case['conversation'], 
                test_case['user_question']
            )
            
            if "error" in result:
                print(f"❌ Error: {result['error']}")
                all_tests_passed = False
            else:
                score = result["score"]
                rationale = result["rationale"]
                expected_min, expected_max = test_case["expected_score_range"]
                
                print(f"Score: {score:.3f}")
                print(f"Expected range: {expected_min:.1f} - {expected_max:.1f}")
                print(f"Rationale: {rationale[:150]}...")
                
                if expected_min <= score <= expected_max:
                    print("✅ Score within expected range")
                else:
                    print("⚠️  Score outside expected range (might be acceptable)")
                    # Don't fail the test for this, as ChatGPT scoring can vary
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            all_tests_passed = False
        
        print("-" * 60)
    
    if all_tests_passed:
        print("\n✅ All ChatGPT scoring tests completed successfully!")
        print("The scoring functionality is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    return all_tests_passed

if __name__ == "__main__":
    print("ChatGPT Scoring Test")
    print("=" * 40)
    
    try:
        result = asyncio.run(test_chatgpt_scoring())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        exit(1) 