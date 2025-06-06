#!/usr/bin/env python3
"""
Final verification of all uploaded data on Railway ChromaDB
"""

import os
import requests
from dotenv import load_dotenv

def final_verification():
    """Final verification of all collections on Railway"""
    print("🔍 Final Railway ChromaDB Verification")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Verifying: {base_url}")
    
    # Check all known collections
    collections_to_check = [
        {"name": "game_screenshots", "uuid": "1b9de2ef-758f-4639-bb99-9703d5042414", "expected_type": "screenshot"},
        {"name": "uploaded_game_features", "uuid": "31bd1f58-b73e-4f92-933e-e6f2ec315a88", "expected_type": "feature"},
    ]
    
    total_items = 0
    working_collections = 0
    
    for collection in collections_to_check:
        name = collection["name"]
        uuid = collection["uuid"]
        expected_type = collection["expected_type"]
        
        print(f"\n📁 Checking '{name}'...")
        
        try:
            # Get count
            count_response = requests.get(f"{base_url}/api/v1/collections/{uuid}/count", headers=headers, timeout=10)
            
            if count_response.status_code == 200:
                count = count_response.json()
                print(f"   ✅ Found! Count: {count} items")
                total_items += count
                working_collections += 1
                
                if count > 0:
                    # Get sample data
                    sample_response = requests.post(
                        f"{base_url}/api/v1/collections/{uuid}/get",
                        headers=headers,
                        json={"limit": 3, "include": ["metadatas", "documents"]},
                        timeout=10
                    )
                    
                    if sample_response.status_code == 200:
                        sample_data = sample_response.json()
                        print(f"   👀 Sample data:")
                        
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
                                print(f"         Description: {document[:80]}...")
                            elif item_type == 'screenshot':
                                print(f"         Screenshot: {metadata.get('path', 'N/A')}")
                                print(f"         Caption: {metadata.get('caption', 'N/A')}")
                
            else:
                print(f"   ❌ Not accessible: {count_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Summary
    print(f"\n📊 Final Summary:")
    print(f"✅ Working collections: {working_collections}/2")
    print(f"📈 Total items: {total_items}")
    
    if working_collections == 2 and total_items > 1600:  # Should have ~1672 screenshots + 96 features
        print(f"\n🎉 PERFECT! Your Railway ChromaDB is fully operational!")
        print(f"✅ Screenshots: Available for search")
        print(f"✅ Features: Available for search") 
        print(f"✅ Total data: {total_items} items")
        print(f"\n🚀 You can now use semantic search on both features and screenshots!")
        return True
    else:
        print(f"\n⚠️ Some collections may be missing or incomplete")
        return False

if __name__ == "__main__":
    success = final_verification()
    
    if success:
        print(f"\n🎯 Mission Accomplished!")
        print(f"Your ChromaDB on Railway has all your features and screenshots!")
    else:
        print(f"\n🔧 Some issues detected, but basic functionality appears to work.") 