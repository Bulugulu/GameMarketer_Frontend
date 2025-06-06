#!/usr/bin/env python3
"""
Comprehensive Railway ChromaDB status check
"""

import os
import requests
import json
from dotenv import load_dotenv

def check_railway_status():
    """Check Railway ChromaDB status and data"""
    print("🔍 Railway ChromaDB Status Check")
    print("=" * 40)
    
    # Load environment variables from root directory
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL")
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    if not base_url or not token:
        print("❌ Missing environment variables")
        print(f"   CHROMA_PUBLIC_URL: {'✅' if base_url else '❌'}")
        print(f"   CHROMA_SERVER_AUTHN_CREDENTIALS: {'✅' if token else '❌'}")
        return False
    
    base_url = base_url.rstrip('/')
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Checking: {base_url}")
    print(f"🔑 Token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
    
    try:
        # Step 1: Basic connectivity
        print("\n1️⃣ Testing basic connectivity...")
        response = requests.get(base_url, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
        if response.status_code == 502:
            print("   ❌ 502 Bad Gateway - Service is down or starting")
            print("   This usually means Railway is restarting or crashed")
            return False
        elif response.status_code == 200:
            print("   ✅ Service is responding")
        elif response.status_code == 404:
            print("   ⚠️ 404 - Main page not found, but service might be running")
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
        
        # Step 2: Heartbeat
        print("\n2️⃣ Testing heartbeat...")
        response = requests.get(f"{base_url}/api/v1/heartbeat", headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Heartbeat successful")
        elif response.status_code == 502:
            print("   ❌ 502 - ChromaDB service is down")
            return False
        else:
            print(f"   ❌ Heartbeat failed with status {response.status_code}")
        
        # Step 3: Version
        print("\n3️⃣ Testing version...")
        response = requests.get(f"{base_url}/api/v1/version", headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Version check successful")
        else:
            print(f"   ❌ Version check failed")
        
        # Step 4: List collections
        print("\n4️⃣ Testing collections...")
        response = requests.get(f"{base_url}/api/v1/collections", headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            collections = response.json()
            print(f"   ✅ Found {len(collections)} collections:")
            
            for collection in collections:
                name = collection.get('name', 'Unknown')
                uuid = collection.get('id', collection.get('uuid', 'Unknown'))
                print(f"      - {name} (UUID: {uuid})")
                
                # Get count for each collection
                try:
                    count_response = requests.get(
                        f"{base_url}/api/v1/collections/{uuid}/count", 
                        headers=headers, 
                        timeout=15
                    )
                    if count_response.status_code == 200:
                        count = count_response.json()
                        print(f"        📊 Count: {count} items")
                    else:
                        print(f"        ❌ Count failed ({count_response.status_code}): {count_response.text}")
                except Exception as e:
                    print(f"        ❌ Count error: {str(e)}")
            
            return True
        else:
            print(f"   ❌ Collections list failed")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timeout - service is slow or down")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = check_railway_status()
        
        if not success:
            print("\n🔧 Troubleshooting Steps:")
            print("1. Check Railway dashboard - is the ChromaDB service running?")
            print("2. Look at Railway logs for error messages")
            print("3. Try restarting the service")
            print("4. Verify service has enough resources")
            print("5. Check if deployment is still in progress")
        else:
            print("\n🎉 Railway ChromaDB is working!")
    except Exception as e:
        print(f"\n❌ Script error: {str(e)}")
        import traceback
        traceback.print_exc() 