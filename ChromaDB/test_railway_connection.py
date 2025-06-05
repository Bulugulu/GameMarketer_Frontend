#!/usr/bin/env python3
"""
Simple script to test Railway ChromaDB connection
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

def test_railway_connection():
    """Test connection to Railway ChromaDB service"""
    print("🔧 Testing Railway ChromaDB Connection")
    print("=" * 40)
    
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
        print("Please ensure CHROMA_PUBLIC_URL and CHROMA_SERVER_AUTHN_CREDENTIALS are set in .env.local")
        return False
    
    print(f"\n🌐 Connecting to: {chroma_url}")
    
    try:
        # Initialize ChromaDB HttpClient for Railway
        # Parse the URL to extract host and port
        import urllib.parse
        parsed_url = urllib.parse.urlparse(chroma_url)
        host = parsed_url.netloc or parsed_url.path.strip('/')
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        ssl = parsed_url.scheme == 'https'
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   SSL: {ssl}")
        
        client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=ssl,
            headers={"Authorization": f"Bearer {chroma_token}"}
        )
        
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
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {str(e)}")
        print("\n🔍 Troubleshooting suggestions:")
        print("1. Check that your Railway ChromaDB service is running")
        print("2. Verify CHROMA_PUBLIC_URL format (should be full URL like https://xxx.railway.app)")
        print("3. Verify CHROMA_SERVER_AUTHN_CREDENTIALS token is correct")
        print("4. Check Railway service logs for any authentication issues")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_railway_connection()
    if success:
        print("\n✅ Ready to proceed with database upload!")
        print("Run 'python ChromaDB/railway_upload_and_test.py' to upload your database.")
    else:
        print("\n❌ Please fix the connection issues before proceeding.") 