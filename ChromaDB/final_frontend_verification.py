#!/usr/bin/env python3
"""
Final verification that front-end collections are properly configured
"""

import os
import requests
from dotenv import load_dotenv

def final_frontend_verification():
    """Final verification that both collections work for front-end"""
    print("🔍 Final Front-End Verification")
    print("=" * 35)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Verifying: {base_url}")
    
    # Check the collections that the front-end expects
    collections_to_verify = [
        {
            "name": "game_features", 
            "uuid": "f5a365d3-2409-4354-8106-378e22f0bea5", 
            "expected_type": "feature",
            "frontend_expectation": "ChromaDBManager.search_features()"
        },
        {
            "name": "game_screenshots", 
            "uuid": "1b9de2ef-758f-4639-bb99-9703d5042414", 
            "expected_type": "screenshot",
            "frontend_expectation": "ChromaDBManager.search_screenshots()"
        },
    ]
    
    total_items = 0
    working_collections = 0
    
    for collection in collections_to_verify:
        name = collection["name"]
        uuid = collection["uuid"]
        expected_type = collection["expected_type"]
        frontend_expectation = collection["frontend_expectation"]
        
        print(f"\n📁 Verifying '{name}' for {frontend_expectation}...")
        
        try:
            # Get count
            count_response = requests.get(f"{base_url}/api/v1/collections/{uuid}/count", headers=headers, timeout=10)
            
            if count_response.status_code == 200:
                count = count_response.json()
                print(f"   ✅ Count: {count} items")
                total_items += count
                working_collections += 1
                
                if count > 0:
                    # Get sample data to verify structure
                    sample_response = requests.post(
                        f"{base_url}/api/v1/collections/{uuid}/get",
                        headers=headers,
                        json={"limit": 2, "include": ["metadatas", "documents"]},
                        timeout=10
                    )
                    
                    if sample_response.status_code == 200:
                        sample_data = sample_response.json()
                        print(f"   👀 Sample data structure:")
                        
                        for i, (doc_id, metadata, document) in enumerate(zip(
                            sample_data.get('ids', []),
                            sample_data.get('metadatas', []),
                            sample_data.get('documents', [])
                        )):
                            item_type = metadata.get('type', 'unknown')
                            print(f"      {i+1}. ID: {doc_id}")
                            print(f"         Type: {item_type} ({'✅' if item_type == expected_type else '❌'})")
                            
                            if item_type == 'feature':
                                print(f"         Feature: {metadata.get('name', 'N/A')}")
                                print(f"         Feature ID: {metadata.get('feature_id', 'N/A')}")
                                print(f"         Game ID: {metadata.get('game_id', 'N/A')}")
                            elif item_type == 'screenshot':
                                print(f"         Screenshot: {metadata.get('path', 'N/A')}")
                                print(f"         Caption: {metadata.get('caption', 'N/A')[:50]}...")
                                print(f"         Screenshot ID: {metadata.get('screenshot_id', 'N/A')}")
                
            else:
                print(f"   ❌ Not accessible: {count_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Summary
    print(f"\n📊 Front-End Verification Summary:")
    print(f"✅ Working collections: {working_collections}/2")
    print(f"📈 Total items: {total_items}")
    
    if working_collections == 2 and total_items > 1600:  # Should have ~1672 screenshots + 96 features
        print(f"\n🎉 PERFECT! Front-end is fully configured!")
        print(f"✅ semantic_search_tool will find:")
        print(f"   - Features: ✅ game_features collection ({collections_to_verify[0]['uuid']})")
        print(f"   - Screenshots: ✅ game_screenshots collection ({collections_to_verify[1]['uuid']})")
        print(f"\n🚀 Your agent_tools.py semantic search should now work correctly!")
        return True
    else:
        print(f"\n⚠️ Configuration issue detected")
        return False

if __name__ == "__main__":
    success = final_frontend_verification()
    
    if success:
        print(f"\n🎯 FRONT-END FIXED!")
        print(f"Your semantic feature search should now work properly!")
    else:
        print(f"\n🔧 Some configuration issues remain.") 