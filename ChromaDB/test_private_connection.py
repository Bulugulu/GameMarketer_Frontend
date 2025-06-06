#!/usr/bin/env python3
"""
Test ChromaDB connection using private network
"""

import os
import requests
from dotenv import load_dotenv

def test_private_connection():
    """Test ChromaDB using private network URL"""
    print("🔍 Testing ChromaDB Private Network Connection")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    # Try both public and private URLs
    public_url = os.getenv("CHROMA_PUBLIC_URL")
    private_url = os.getenv("CHROMA_PRIVATE_URL")
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    print(f"🌐 Public URL: {public_url}")
    print(f"🔒 Private URL: {private_url}")
    print(f"🔑 Token: {'✅ Found' if token else '❌ Missing'}")
    
    if not token:
        print("❌ Missing CHROMA_SERVER_AUTHN_CREDENTIALS")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test public URL (should fail if CHROMA_HOST_ADDR is set to ::)
    if public_url:
        print(f"\n1️⃣ Testing PUBLIC URL: {public_url}")
        try:
            response = requests.get(f"{public_url}/api/v1/heartbeat", headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Public network is working")
            elif response.status_code == 502:
                print("   ❌ Public network connection refused (expected with CHROMA_HOST_ADDR=::)")
        except Exception as e:
            print(f"   ❌ Public network error: {str(e)}")
    
    # Test private URL (should work if CHROMA_HOST_ADDR is set to ::)
    if private_url:
        print(f"\n2️⃣ Testing PRIVATE URL: {private_url}")
        try:
            response = requests.get(f"{private_url}/api/v1/heartbeat", headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Private network is working!")
                
                # Test collections
                collections_response = requests.get(f"{private_url}/api/v1/collections", headers=headers, timeout=10)
                if collections_response.status_code == 200:
                    collections = collections_response.json()
                    print(f"   ✅ Found {len(collections)} collections:")
                    for collection in collections:
                        name = collection.get('name', 'Unknown')
                        uuid = collection.get('id', collection.get('uuid', 'Unknown'))
                        print(f"      - {name} (UUID: {uuid})")
                        
                        # Get count
                        count_response = requests.get(f"{private_url}/api/v1/collections/{uuid}/count", headers=headers, timeout=10)
                        if count_response.status_code == 200:
                            count = count_response.json()
                            print(f"        📊 Count: {count} items")
                
                return True
            else:
                print(f"   ❌ Private network failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Private network error: {str(e)}")
    else:
        print("\n❌ CHROMA_PRIVATE_URL not found in environment variables")
    
    return False

if __name__ == "__main__":
    test_private_connection() 