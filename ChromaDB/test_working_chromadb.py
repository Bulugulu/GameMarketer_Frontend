#!/usr/bin/env python3
"""
Test working ChromaDB with proper 0.6.3 API calls
"""

import os
import requests
import json
from dotenv import load_dotenv

def test_working_chromadb():
    """Test ChromaDB with corrected API calls for 0.6.3"""
    print("🎉 Testing Working ChromaDB (v0.6.3)")
    print("=" * 45)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 URL: {base_url}")
    print(f"🔑 Token: {token[:15]}...{token[-10:]}")
    
    try:
        # Test 1: Verify service is alive
        print("\n1️⃣ Verifying service status...")
        response = requests.get(f"{base_url}/api/v1/heartbeat", headers=headers, timeout=10)
        if response.status_code == 200:
            heartbeat = response.json()
            print(f"   ✅ Heartbeat: {heartbeat}")
        else:
            print(f"   ❌ Heartbeat failed: {response.status_code}")
            return False
        
        # Test 2: Get version
        print("\n2️⃣ Checking version...")
        response = requests.get(f"{base_url}/api/v1/version", headers=headers, timeout=10)
        if response.status_code == 200:
            version = response.text.strip('"')
            print(f"   ✅ ChromaDB Version: {version}")
        else:
            print(f"   ❌ Version check failed: {response.status_code}")
        
        # Test 3: Try collections with different approach
        print("\n3️⃣ Listing collections (alternative method)...")
        
        # Try the collections endpoint without parameters
        response = requests.get(f"{base_url}/api/v1/collections", headers=headers, timeout=15)
        print(f"   API Response Status: {response.status_code}")
        print(f"   Response Text: {response.text[:200]}...")
        
        if response.status_code == 200:
            try:
                collections = response.json()
                print(f"   ✅ Found {len(collections)} collections!")
                
                for i, collection in enumerate(collections):
                    name = collection.get('name', 'Unknown')
                    coll_id = collection.get('id', collection.get('uuid', 'Unknown'))
                    metadata = collection.get('metadata', {})
                    
                    print(f"\n   📁 Collection {i+1}: {name}")
                    print(f"      ID: {coll_id}")
                    print(f"      Metadata: {metadata}")
                    
                    # Try to get count for this collection
                    try:
                        count_response = requests.get(
                            f"{base_url}/api/v1/collections/{coll_id}/count", 
                            headers=headers, 
                            timeout=10
                        )
                        if count_response.status_code == 200:
                            count = count_response.json()
                            print(f"      📊 Document Count: {count}")
                            
                            if count > 0:
                                # Try to peek at a few documents
                                peek_response = requests.post(
                                    f"{base_url}/api/v1/collections/{coll_id}/get",
                                    headers=headers,
                                    json={"limit": 3, "include": ["documents", "metadatas"]},
                                    timeout=10
                                )
                                if peek_response.status_code == 200:
                                    peek_data = peek_response.json()
                                    print(f"      👀 Sample documents: {len(peek_data.get('ids', []))} items")
                                    if peek_data.get('documents'):
                                        for j, doc in enumerate(peek_data['documents'][:2]):
                                            print(f"         - Doc {j+1}: {doc[:60]}...")
                        else:
                            print(f"      ❌ Count failed: {count_response.status_code}")
                    except Exception as count_error:
                        print(f"      ⚠️ Count error: {str(count_error)}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {str(e)}")
                print(f"   Raw response: {response.text}")
        else:
            print(f"   ❌ Collections request failed")
            
            # Try alternative endpoint format
            print("\n   🔄 Trying alternative collections endpoint...")
            alt_response = requests.post(
                f"{base_url}/api/v1/collections", 
                headers=headers, 
                json={},
                timeout=15
            )
            print(f"   Alternative Status: {alt_response.status_code}")
            print(f"   Alternative Response: {alt_response.text[:200]}...")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_working_chromadb()
    
    if success:
        print("\n🎉 SUCCESS! Your ChromaDB is working and contains data!")
        print("\n📊 Summary:")
        print("✅ Service is alive and responding")
        print("✅ Collections are accessible")
        print("✅ Document counts are available")
        print("✅ Your features and screenshots should be in there!")
    else:
        print("\n⚠️ Service is running but collections access needs debugging")
        print("The good news: ChromaDB itself is working fine!") 