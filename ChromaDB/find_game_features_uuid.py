#!/usr/bin/env python3
"""
Find the game_features collection UUID using Railway HTTP client
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv('../.env.local')

sys.path.append('.')

from railway_http_client import RailwayHTTPChromaClient

def find_game_features_uuid():
    """Find the game_features collection UUID"""
    print("🔍 Finding game_features Collection UUID")
    print("=" * 40)
    
    try:
        # Use the Railway HTTP client that we know works
        client = RailwayHTTPChromaClient()
        
        # Test basic connection
        print("1️⃣ Testing connection...")
        version = client.get_version()
        print(f"   ✅ ChromaDB Version: {version}")
        
        # Try to create the game_features collection to get its UUID
        print("\n2️⃣ Attempting to get/create game_features collection...")
        
        # This should either create it or return the existing one
        features_uuid = client.create_collection("game_features", {"description": "Game features for semantic search"})
        
        if features_uuid:
            print(f"   ✅ game_features UUID: {features_uuid}")
            
            # Check if it has any data
            count = client.get_collection_count("game_features")
            print(f"   📊 Current count: {count} items")
            
            if count == 0:
                print("   📝 Collection is empty - ready for upload!")
                return features_uuid
            else:
                print("   📋 Collection has data - checking content...")
                
                # Get a sample to see what type of data it has
                import requests
                from dotenv import load_dotenv
                
                load_dotenv('../.env.local')
                base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
                token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                sample_response = requests.post(
                    f"{base_url}/api/v1/collections/{features_uuid}/get",
                    headers=headers,
                    json={"limit": 3, "include": ["metadatas"]},
                    timeout=10
                )
                
                if sample_response.status_code == 200:
                    sample_data = sample_response.json()
                    print(f"   👀 Sample content:")
                    for i, metadata in enumerate(sample_data.get('metadatas', [])):
                        print(f"      {i+1}. Type: {metadata.get('type', 'unknown')}")
                        if metadata.get('type') == 'feature':
                            print(f"         Feature: {metadata.get('name', 'N/A')}")
                
                return features_uuid
        else:
            print("   ❌ Failed to get game_features collection UUID")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    uuid = find_game_features_uuid()
    
    if uuid:
        print(f"\n🎉 Found game_features UUID: {uuid}")
        print("You can now upload your features to this collection!")
    else:
        print("\n❌ Could not find game_features collection UUID") 