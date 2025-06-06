#!/usr/bin/env python3
"""
Find the game_features collection UUID using various strategies
"""

import os
import requests
import uuid
from dotenv import load_dotenv

def find_features_collection():
    """Try to find the game_features collection UUID"""
    print("🔍 Searching for game_features Collection")
    print("=" * 45)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Searching on: {base_url}")
    
    # Strategy 1: Try UUID variations around the known screenshots UUID
    known_uuid = "1b9de2ef-758f-4639-bb99-9703d5042414"
    print(f"\n📋 Strategy 1: UUID variations around known screenshot UUID")
    print(f"   Known screenshots UUID: {known_uuid}")
    
    # Strategy 2: Try common UUID patterns
    # ChromaDB sometimes generates UUIDs sequentially or with patterns
    base_parts = known_uuid.split('-')
    
    uuid_candidates = []
    
    # Try incrementing/decrementing the last part
    try:
        last_part = base_parts[-1]
        last_num = int(last_part, 16)
        
        for offset in [-10, -5, -1, 1, 5, 10]:
            new_num = last_num + offset
            if new_num >= 0:
                new_last = f"{new_num:012x}"  # Pad to 12 hex digits
                new_uuid = '-'.join(base_parts[:-1] + [new_last])
                uuid_candidates.append(new_uuid)
    except:
        pass
    
    # Try some other common UUID candidates based on creation time
    # Features are often created before screenshots
    uuid_candidates.extend([
        "1b9de2ef-758f-4639-bb99-9703d5042413",  # One before
        "1b9de2ef-758f-4639-bb99-9703d5042412",  # Two before
        "1b9de2ef-758f-4639-bb99-9703d5042415",  # One after
        "1b9de2ef-758f-4639-bb99-9703d5042411",  # Three before
    ])
    
    print(f"   Testing {len(uuid_candidates)} UUID candidates...")
    
    found_uuids = []
    
    for i, candidate_uuid in enumerate(uuid_candidates):
        try:
            count_response = requests.get(
                f"{base_url}/api/v1/collections/{candidate_uuid}/count", 
                headers=headers, 
                timeout=5
            )
            
            if count_response.status_code == 200:
                count = count_response.json()
                print(f"   ✅ FOUND! UUID: {candidate_uuid} -> {count} items")
                found_uuids.append({"uuid": candidate_uuid, "count": count})
                
                # Try to get metadata to confirm it's features
                try:
                    sample_response = requests.post(
                        f"{base_url}/api/v1/collections/{candidate_uuid}/get",
                        headers=headers,
                        json={"limit": 1, "include": ["metadatas"]},
                        timeout=5
                    )
                    
                    if sample_response.status_code == 200:
                        sample_data = sample_response.json()
                        if sample_data.get('metadatas') and len(sample_data['metadatas']) > 0:
                            metadata = sample_data['metadatas'][0]
                            collection_type = metadata.get('type', 'unknown')
                            print(f"      Type: {collection_type}")
                            
                            if collection_type == 'feature':
                                print(f"      🎯 This is likely the game_features collection!")
                                print(f"      Feature ID: {metadata.get('feature_id', 'N/A')}")
                                print(f"      Feature Name: {metadata.get('name', 'N/A')}")
                except Exception as e:
                    print(f"      ⚠️ Couldn't get metadata: {str(e)}")
                    
            elif count_response.status_code != 404:
                print(f"   ⚠️ UUID {candidate_uuid} -> {count_response.status_code}")
                
        except Exception as e:
            # Silently continue for connection errors
            pass
    
    # Strategy 3: Try to recreate the collection and see what UUID it gets
    print(f"\n📋 Strategy 3: Create test collection to understand UUID pattern")
    try:
        test_data = {
            "name": "uuid_test_collection",
            "metadata": {"description": "Test to understand UUID pattern"},
            "get_or_create": True
        }
        
        create_response = requests.post(
            f"{base_url}/api/v1/collections", 
            headers=headers, 
            json=test_data,
            timeout=10
        )
        
        if create_response.status_code == 200:
            result = create_response.json()
            test_uuid = result.get('id', result.get('uuid', 'unknown'))
            print(f"   Test collection UUID: {test_uuid}")
            
            # Compare with known UUID to understand pattern
            if test_uuid != 'unknown':
                print(f"   Screenshots UUID:     {known_uuid}")
                print(f"   New test UUID:        {test_uuid}")
                
            # Clean up test collection
            try:
                requests.delete(f"{base_url}/api/v1/collections/{test_uuid}", headers=headers, timeout=5)
                print(f"   🧹 Test collection cleaned up")
            except:
                pass
                
    except Exception as e:
        print(f"   ❌ Strategy 3 failed: {str(e)}")
    
    # Summary
    print(f"\n📊 Summary:")
    if found_uuids:
        print(f"✅ Found {len(found_uuids)} collections:")
        for coll in found_uuids:
            print(f"   - UUID: {coll['uuid']} -> {coll['count']} items")
    else:
        print("❌ No additional collections found with tested UUIDs")
        print("The game_features collection might:")
        print("  1. Have a completely different UUID pattern")
        print("  2. Not have been uploaded successfully")
        print("  3. Have been deleted or reset")
    
    return found_uuids

if __name__ == "__main__":
    collections = find_features_collection()
    
    if collections:
        print(f"\n🎉 SUCCESS! Found {len(collections)} additional collections!")
    else:
        print("\n🤔 No additional collections found with UUID search strategy") 