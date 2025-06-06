#!/usr/bin/env python3
"""
Check what's in the existing game_features collection
"""

import os
import requests
from dotenv import load_dotenv

def check_existing_game_features():
    """Check the existing game_features collection"""
    print("🔍 Checking Existing 'game_features' Collection")
    print("=" * 45)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # We know from the Railway test that game_features exists
    # Let's try to find its UUID by testing known patterns
    
    potential_uuids = [
        # Try some variations around the screenshots UUID
        "1b9de2ef-758f-4639-bb99-9703d5042413",  # One before screenshots
        "1b9de2ef-758f-4639-bb99-9703d5042412",  # Two before screenshots  
        "1b9de2ef-758f-4639-bb99-9703d5042411",  # Three before
        "1b9de2ef-758f-4639-bb99-9703d5042410",  # Four before
        "1b9de2ef-758f-4639-bb99-9703d5042415",  # One after
        "1b9de2ef-758f-4639-bb99-9703d5042416",  # Two after
    ]
    
    print("🔍 Searching for 'game_features' collection UUID...")
    
    for test_uuid in potential_uuids:
        try:
            count_response = requests.get(f"{base_url}/api/v1/collections/{test_uuid}/count", headers=headers, timeout=5)
            if count_response.status_code == 200:
                count = count_response.json()
                print(f"✅ Found collection at {test_uuid} with {count} items")
                
                # Check if this has features-like content
                if count > 0:
                    sample_response = requests.post(
                        f"{base_url}/api/v1/collections/{test_uuid}/get",
                        headers=headers,
                        json={"limit": 3, "include": ["metadatas", "documents"]},
                        timeout=5
                    )
                    
                    if sample_response.status_code == 200:
                        sample_data = sample_response.json()
                        print(f"👀 Sample data from {test_uuid}:")
                        
                        for i, (doc_id, metadata, document) in enumerate(zip(
                            sample_data.get('ids', []),
                            sample_data.get('metadatas', []),
                            sample_data.get('documents', [])
                        )):
                            print(f"   {i+1}. ID: {doc_id}")
                            print(f"      Type: {metadata.get('type', 'unknown')}")
                            if metadata.get('type') == 'feature':
                                print(f"      Feature: {metadata.get('name', 'N/A')}")
                            elif metadata.get('type') == 'screenshot':
                                print(f"      Screenshot: {metadata.get('path', 'N/A')}")
                            print(f"      Document: {document[:60]}...")
                            print()
                else:
                    print(f"   Collection {test_uuid} is empty")
                
        except Exception as e:
            continue
    
    print("\n📋 Summary:")
    print("If we found a collection with 'type': 'feature', that's likely the game_features collection.")
    print("If we found an empty collection, we might need to upload to that one.")

if __name__ == "__main__":
    check_existing_game_features() 