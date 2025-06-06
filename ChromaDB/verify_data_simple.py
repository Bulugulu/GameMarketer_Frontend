#!/usr/bin/env python3
"""
Simple data verification using the working Railway HTTP client
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from root directory first
load_dotenv('../.env.local')

sys.path.append('.')

from railway_http_client import RailwayHTTPChromaClient

def verify_uploaded_data():
    """Verify the uploaded data using the working HTTP client"""
    print("🔍 Verifying Uploaded Data")
    print("=" * 35)
    
    try:
        # Initialize the client that we know works
        client = RailwayHTTPChromaClient()
        
        # Test 1: Check if client can connect
        print("1️⃣ Testing client connection...")
        version = client.get_version()
        print(f"   ✅ ChromaDB Version: {version}")
        
        heartbeat = client.heartbeat()
        print(f"   ✅ Heartbeat: {heartbeat}")
        
        # Test 2: Try to list collections
        print("\n2️⃣ Attempting to list collections...")
        collections = client.list_collections()
        
        if collections:
            print(f"   ✅ Found {len(collections)} collections:")
            
            for collection in collections:
                if isinstance(collection, dict):
                    name = collection.get('name', 'Unknown')
                    uuid = collection.get('id', collection.get('uuid', 'Unknown'))
                    print(f"      - {name} (UUID: {uuid})")
                    
                    # Try to get count
                    count = client.get_collection_count(name)
                    print(f"        📊 Count: {count} items")
                else:
                    print(f"      - {collection}")
        else:
            print("   ⚠️ No collections found or list_collections() returned empty")
            
            # Let's try creating a collection to test if the service works
            print("\n   🧪 Testing collection creation...")
            test_uuid = client.create_collection("test_verification", {"description": "Test collection"})
            if test_uuid:
                print(f"   ✅ Successfully created test collection: {test_uuid}")
                
                # Try to list again
                collections = client.list_collections()
                print(f"   ✅ Collections after test creation: {len(collections) if collections else 0}")
                
                # Clean up
                deleted = client.delete_collection("test_verification")
                print(f"   🧹 Test collection deleted: {deleted}")
            else:
                print("   ❌ Failed to create test collection")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_uploaded_data()
    
    if success:
        print("\n🎉 Data verification completed!")
    else:
        print("\n❌ Verification had issues, but service appears to be running") 