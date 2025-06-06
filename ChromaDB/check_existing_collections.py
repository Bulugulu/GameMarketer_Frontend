#!/usr/bin/env python3
"""
Check existing collections by UUID, bypassing the broken list API
"""

import os
import requests
from dotenv import load_dotenv

def check_collections_by_uuid():
    """Check collections by trying known UUIDs"""
    print("🔍 Checking Existing Collections by UUID")
    print("=" * 45)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Known collection UUIDs from your upload scripts
    collection_candidates = [
        {"name": "game_screenshots", "uuid": "1b9de2ef-758f-4639-bb99-9703d5042414"},
        {"name": "game_features", "uuid": None},  # We'll try to find this
        {"name": "test_verification", "uuid": "d95871b0-d128-4b50-a2f3-5d60a8824f14"},  # Just created
    ]
    
    found_collections = []
    
    for collection in collection_candidates:
        name = collection["name"]
        uuid = collection["uuid"]
        
        print(f"\n📁 Checking '{name}'...")
        
        if uuid:
            # Try to get count for this collection
            try:
                count_response = requests.get(
                    f"{base_url}/api/v1/collections/{uuid}/count", 
                    headers=headers, 
                    timeout=10
                )
                
                if count_response.status_code == 200:
                    count = count_response.json()
                    print(f"   ✅ Found! UUID: {uuid}")
                    print(f"   📊 Document Count: {count}")
                    found_collections.append({"name": name, "uuid": uuid, "count": count})
                    
                    # Try to get a few sample documents
                    if count > 0:
                        try:
                            sample_response = requests.post(
                                f"{base_url}/api/v1/collections/{uuid}/get",
                                headers=headers,
                                json={"limit": 2, "include": ["documents", "metadatas"]},
                                timeout=10
                            )
                            
                            if sample_response.status_code == 200:
                                sample_data = sample_response.json()
                                print(f"   👀 Sample data retrieved: {len(sample_data.get('ids', []))} items")
                                
                                # Show sample metadata to understand structure
                                if sample_data.get('metadatas'):
                                    metadata = sample_data['metadatas'][0]
                                    print(f"   📋 Sample metadata keys: {list(metadata.keys())}")
                                    
                                    # Show specific info based on collection type
                                    if name == "game_screenshots":
                                        print(f"      - Screenshot path: {metadata.get('path', 'N/A')}")
                                        print(f"      - Caption: {metadata.get('caption', 'N/A')[:50]}...")
                                    elif name == "game_features":
                                        print(f"      - Feature name: {metadata.get('name', 'N/A')}")
                                        print(f"      - Feature type: {metadata.get('type', 'N/A')}")
                            else:
                                print(f"   ⚠️ Couldn't retrieve sample data: {sample_response.status_code}")
                        except Exception as e:
                            print(f"   ⚠️ Sample data error: {str(e)}")
                else:
                    print(f"   ❌ Not found or error: {count_response.status_code}")
                    if count_response.status_code != 404:
                        print(f"      Response: {count_response.text[:100]}...")
                        
            except Exception as e:
                print(f"   ❌ Error checking UUID {uuid}: {str(e)}")
        else:
            print(f"   ⚠️ No UUID provided - would need to guess or search")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"✅ Found {len(found_collections)} collections:")
    
    total_items = 0
    for coll in found_collections:
        print(f"   - {coll['name']}: {coll['count']} items")
        total_items += coll['count']
    
    print(f"📈 Total items across all collections: {total_items}")
    
    if len(found_collections) == 0:
        print("⚠️ No collections found with known UUIDs")
        print("This could mean:")
        print("  1. Collections have different UUIDs than expected")
        print("  2. Collections were not uploaded successfully")
        print("  3. Collections were deleted or reset")
    
    return found_collections

if __name__ == "__main__":
    collections = check_collections_by_uuid()
    
    if collections:
        print(f"\n🎉 SUCCESS! Found {len(collections)} collections with data!")
        print("Your ChromaDB on Railway contains your uploaded data!")
    else:
        print("\n🤔 No collections found with expected UUIDs")
        print("But the service is definitely working - we can create new collections") 