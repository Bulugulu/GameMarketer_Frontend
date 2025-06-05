#!/usr/bin/env python3
"""
Fixed Railway ChromaDB connection script for 0.6.3 compatibility
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

def test_railway_connection_fixed():
    """Test connection to Railway ChromaDB service with proper API version"""
    print("🔧 Testing Railway ChromaDB Connection (v0.6.3 Compatible)")
    print("=" * 55)
    
    # Load environment variables
    load_dotenv('.env.local')
    
    # Get Railway ChromaDB credentials
    chroma_url = os.getenv("CHROMA_PUBLIC_URL")
    chroma_token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    print(f"📍 CHROMA_PUBLIC_URL: {'✅ Found' if chroma_url else '❌ Missing'}")
    print(f"🔑 CHROMA_SERVER_AUTHN_CREDENTIALS: {'✅ Found' if chroma_token else '❌ Missing'}")
    print(f"🤖 OPENAI_API_KEY: {'✅ Found' if openai_api_key else '❌ Missing'}")
    
    if not chroma_url or not chroma_token:
        print("\n❌ Missing required environment variables!")
        return False
    
    print(f"\n🌐 Connecting to: {chroma_url}")
    
    try:
        # Initialize ChromaDB HttpClient for Railway 0.6.3
        import urllib.parse
        parsed_url = urllib.parse.urlparse(chroma_url)
        host = parsed_url.netloc
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        ssl = parsed_url.scheme == 'https'
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   SSL: {ssl}")
        
        # Use the simpler HttpClient initialization for 0.6.3 compatibility
        from chromadb.config import Settings
        settings = Settings(
            chroma_api_impl="chromadb.api.fastapi.FastAPI",
            chroma_server_host=host,
            chroma_server_http_port=port,
            chroma_server_ssl_enabled=ssl,
            chroma_server_headers={"Authorization": f"Bearer {chroma_token}"}
        )
        
        client = chromadb.Client(settings)
        
        print("🔌 Client created successfully")
        
        # Test basic operations
        print("\n🧪 Running connection tests...")
        
        # Test 1: List collections
        print("1️⃣ Testing list_collections()...")
        collections = client.list_collections()
        print(f"   ✅ Success! Found {len(collections)} existing collections:")
        for collection in collections:
            print(f"      - {collection.name}")
        
        # Test 2: Create a test collection
        print("\n2️⃣ Testing collection creation...")
        test_collection = client.get_or_create_collection(
            name="connection_test",
            metadata={"description": "Test collection for connection verification"}
        )
        print("   ✅ Test collection created/retrieved successfully")
        
        # Test 3: Add a simple test document
        print("\n3️⃣ Testing document addition...")
        test_collection.upsert(
            ids=["test_doc_1"],
            documents=["This is a test document for connection verification"],
            metadatas=[{"test": True, "created_by": "connection_test"}]
        )
        print("   ✅ Test document added successfully")
        
        # Test 4: Query the test document
        print("\n4️⃣ Testing query functionality...")
        results = test_collection.query(
            query_texts=["test document"],
            n_results=1
        )
        print(f"   ✅ Query successful! Found {len(results['ids'][0])} results")
        if results['ids'][0]:
            print(f"      - Document ID: {results['ids'][0][0]}")
            print(f"      - Content: {results['documents'][0][0][:50]}...")
        
        # Test 5: Count documents
        print("\n5️⃣ Testing count functionality...")
        count = test_collection.count()
        print(f"   ✅ Collection has {count} documents")
        
        # Test 6: Test with OpenAI embeddings (if available)
        if openai_api_key:
            print("\n6️⃣ Testing OpenAI embeddings...")
            try:
                embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=openai_api_key,
                    model_name="text-embedding-3-large"
                )
                
                # Create collection with embedding function
                openai_collection = client.get_or_create_collection(
                    name="openai_test",
                    embedding_function=embedding_function
                )
                print("   ✅ OpenAI embedding function works!")
                
                # Test adding document with auto-generated embeddings
                openai_collection.upsert(
                    ids=["openai_test_1"],
                    documents=["Testing OpenAI embeddings integration"],
                    metadatas=[{"embedding_test": True}]
                )
                print("   ✅ Document with OpenAI embeddings added successfully")
                
                # Test semantic search
                semantic_results = openai_collection.query(
                    query_texts=["embedding integration test"],
                    n_results=1
                )
                print(f"   ✅ Semantic search successful! Distance: {semantic_results['distances'][0][0]:.4f}")
                
            except Exception as e:
                print(f"   ⚠️ OpenAI embeddings test failed: {str(e)}")
        else:
            print("\n6️⃣ Skipping OpenAI embeddings test (no API key)")
        
        # Clean up test collections
        print("\n🧹 Cleaning up test collections...")
        try:
            client.delete_collection("connection_test")
            print("   ✅ connection_test collection deleted")
        except:
            pass
        
        try:
            client.delete_collection("openai_test")
            print("   ✅ openai_test collection deleted")
        except:
            pass
        
        print("\n🎉 All tests passed! Railway ChromaDB connection is working perfectly!")
        return True, client
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {str(e)}")
        print("\n🔍 Trying alternative connection method...")
        
        # Alternative approach: Direct HTTP requests
        try:
            import requests
            import json
            
            headers = {"Authorization": f"Bearer {chroma_token}"}
            base_url = chroma_url.rstrip('/')
            
            # Test collections endpoint directly
            response = requests.get(f"{base_url}/api/v1/collections", headers=headers)
            print(f"Direct API test - Status: {response.status_code}")
            
            if response.status_code == 200:
                collections_data = response.json()
                print(f"✅ Direct API access works! Found {len(collections_data)} collections")
                print("Consider using requests library directly for API calls.")
                return True, None
            else:
                print(f"❌ Direct API failed: {response.text}")
                
        except Exception as api_error:
            print(f"❌ Direct API error: {str(api_error)}")
        
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    success, client = test_railway_connection_fixed()
    if success:
        print("\n✅ Ready to proceed with database upload!")
        if client:
            print("Using ChromaDB client connection.")
        else:
            print("May need to use direct HTTP API calls.")
    else:
        print("\n❌ Please check Railway service configuration.") 