#!/usr/bin/env python3
"""
Diagnostic script for Railway ChromaDB connection issues
"""

import os
import requests
import urllib.parse
from dotenv import load_dotenv

def diagnose_railway_service():
    """Diagnose Railway ChromaDB service connectivity"""
    print("🔧 Railway ChromaDB Service Diagnostics")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('.env.local')
    
    # Get Railway ChromaDB credentials
    chroma_url = os.getenv("CHROMA_PUBLIC_URL")
    chroma_token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    print(f"📍 CHROMA_PUBLIC_URL: {chroma_url}")
    print(f"🔑 Token length: {len(chroma_token) if chroma_token else 0} characters")
    
    if not chroma_url:
        print("❌ CHROMA_PUBLIC_URL not found!")
        return False
    
    # Parse URL
    parsed_url = urllib.parse.urlparse(chroma_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    print(f"\n🌐 Testing connectivity to: {base_url}")
    
    try:
        # Test 1: Basic HTTP connectivity
        print("\n1️⃣ Testing basic HTTP connectivity...")
        response = requests.get(base_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Service is responding!")
        elif response.status_code in [401, 403]:
            print("   ⚠️ Service is running but requires authentication")
        elif response.status_code == 502:
            print("   ❌ 502 Bad Gateway - Service may be starting up or crashed")
        else:
            print(f"   ⚠️ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Connection timeout - service may be down")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error - service may be down")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    try:
        # Test 2: ChromaDB health endpoint
        print("\n2️⃣ Testing ChromaDB health endpoint...")
        health_url = f"{base_url}/api/v1/heartbeat"
        headers = {"Authorization": f"Bearer {chroma_token}"} if chroma_token else {}
        
        response = requests.get(health_url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ ChromaDB health check passed!")
        else:
            print("   ⚠️ Health check failed, trying alternative endpoint...")
            
    except Exception as e:
        print(f"   ⚠️ Health check error: {str(e)}")
    
    try:
        # Test 3: ChromaDB version endpoint
        print("\n3️⃣ Testing ChromaDB version endpoint...")
        version_url = f"{base_url}/api/v1/version"
        headers = {"Authorization": f"Bearer {chroma_token}"} if chroma_token else {}
        
        response = requests.get(version_url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Version endpoint accessible!")
        else:
            print("   ⚠️ Version endpoint failed")
            
    except Exception as e:
        print(f"   ⚠️ Version check error: {str(e)}")
    
    try:
        # Test 4: Collections endpoint
        print("\n4️⃣ Testing ChromaDB collections endpoint...")
        collections_url = f"{base_url}/api/v1/collections"
        headers = {"Authorization": f"Bearer {chroma_token}"} if chroma_token else {}
        
        response = requests.get(collections_url, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("   ✅ Collections endpoint accessible!")
            return True
        elif response.status_code == 401:
            print("   ❌ Authentication failed - check your token")
        elif response.status_code == 502:
            print("   ❌ 502 Bad Gateway - Service is not responding properly")
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Collections endpoint error: {str(e)}")
    
    print("\n🔍 Troubleshooting Recommendations:")
    print("1. Check Railway dashboard - is the ChromaDB service running?")
    print("2. Check Railway logs for any error messages")
    print("3. Try restarting the ChromaDB service in Railway")
    print("4. Verify the service has sufficient resources (CPU/Memory)")
    print("5. Check if the service is still deploying")
    
    return False

if __name__ == "__main__":
    success = diagnose_railway_service()
    if success:
        print("\n✅ Service appears to be working! Try the connection test again.")
    else:
        print("\n❌ Service issues detected. Please check Railway dashboard and logs.") 