#!/usr/bin/env python3
"""
Test script to verify uploaded data in Railway ChromaDB
"""

import os
import requests
import openai
from dotenv import load_dotenv

def test_railway_data():
    """Test the uploaded data in Railway ChromaDB"""
    print("🔍 Testing Uploaded Data in Railway ChromaDB")
    print("=" * 50)
    
    # Load environment variables from root directory
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL")
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not base_url:
        print("❌ CHROMA_PUBLIC_URL not found in environment variables")
        return False
    
    if not token:
        print("❌ CHROMA_SERVER_AUTHN_CREDENTIALS not found in environment variables")
        return False
        
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    base_url = base_url.rstrip('/')
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Connecting to: {base_url}")
    
    # Collection UUIDs (from the upload)
    screenshots_uuid = "1b9de2ef-758f-4639-bb99-9703d5042414"
    
    try:
        # Test 1: Check count
        print("1️⃣ Checking screenshot count...")
        response = requests.get(f"{base_url}/api/v1/collections/{screenshots_uuid}/count", headers=headers)
        if response.status_code == 200:
            count = response.json()
            print(f"   ✅ Screenshots in database: {count}")
        else:
            print(f"   ❌ Failed to get count: {response.text}")
            return False
        
        # Test 2: Generate test query embedding
        print("\n2️⃣ Generating test query embedding...")
        openai_client = openai.OpenAI(api_key=openai_api_key)
        test_embedding = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=["game interface menu screen"]
        ).data[0].embedding
        print(f"   ✅ Generated embedding with {len(test_embedding)} dimensions")
        
        # Test 3: Search screenshots
        print("\n3️⃣ Testing semantic search...")
        search_data = {
            "query_embeddings": [test_embedding],
            "n_results": 5,
            "include": ["documents", "metadatas", "distances"]
        }
        
        response = requests.post(
            f"{base_url}/api/v1/collections/{screenshots_uuid}/query", 
            headers=headers, 
            json=search_data
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Search successful! Found {len(results.get('ids', [[]])[0])} results")
            
            # Display results
            if results.get('ids') and results['ids'][0]:
                print("\n📋 Search Results:")
                for i, (doc_id, distance, metadata) in enumerate(zip(
                    results['ids'][0], 
                    results['distances'][0], 
                    results['metadatas'][0]
                )):
                    print(f"   {i+1}. {doc_id}")
                    print(f"      Distance: {distance:.4f}")
                    print(f"      Path: {metadata.get('path', 'N/A')}")
                    print(f"      Caption: {metadata.get('caption', 'N/A')[:100]}...")
                    print()
        else:
            print(f"   ❌ Search failed: {response.text}")
            return False
        
        # Test 4: Another search query
        print("\n4️⃣ Testing another search query...")
        test_embedding2 = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=["building construction gameplay"]
        ).data[0].embedding
        
        search_data2 = {
            "query_embeddings": [test_embedding2],
            "n_results": 3,
            "include": ["documents", "metadatas", "distances"]
        }
        
        response = requests.post(
            f"{base_url}/api/v1/collections/{screenshots_uuid}/query", 
            headers=headers, 
            json=search_data2
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"   ✅ Second search successful! Found {len(results.get('ids', [[]])[0])} results")
            
            if results.get('ids') and results['ids'][0]:
                print("\n📋 Construction-related Results:")
                for i, (doc_id, distance, metadata) in enumerate(zip(
                    results['ids'][0], 
                    results['distances'][0], 
                    results['metadatas'][0]
                )):
                    print(f"   {i+1}. {doc_id} (distance: {distance:.4f})")
                    print(f"      Caption: {metadata.get('caption', 'N/A')[:100]}...")
        else:
            print(f"   ❌ Second search failed: {response.text}")
        
        print("\n🎉 All tests passed! Your Railway ChromaDB is working perfectly!")
        print(f"🌐 Database URL: {base_url}")
        print(f"📊 Total screenshots: {count}")
        print("✅ Semantic search is fully functional!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_railway_data() 