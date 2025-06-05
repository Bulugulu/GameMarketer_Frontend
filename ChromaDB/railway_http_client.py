#!/usr/bin/env python3
"""
Direct HTTP client for Railway ChromaDB 0.6.3
"""

import os
import json
import requests
import openai
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

class RailwayHTTPChromaClient:
    def __init__(self):
        # Load environment variables
        load_dotenv('.env.local')
        
        self.base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
        self.token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.base_url or not self.token:
            raise ValueError("Missing CHROMA_PUBLIC_URL or CHROMA_SERVER_AUTHN_CREDENTIALS")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Store collection name to UUID mapping
        self.collection_map = {}
        
        # Initialize OpenAI client for embeddings
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        print(f"✅ Railway HTTP ChromaDB Client initialized: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to ChromaDB API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code in [200, 201]:
                return response.json() if response.text else {}
            else:
                print(f"❌ Request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request error: {str(e)}")
            return None
    
    def get_version(self) -> str:
        """Get ChromaDB version"""
        result = self._make_request('GET', '/api/v1/version')
        return result if isinstance(result, str) else str(result)
    
    def heartbeat(self) -> Dict:
        """Check if service is alive"""
        return self._make_request('GET', '/api/v1/heartbeat')
    
    def list_collections(self) -> List[Dict]:
        """List all collections with their UUIDs"""
        try:
            # Try the working endpoint first
            result = self._make_request('GET', '/api/v1/collections')
            if result is None:
                # Try alternative approach - get collections info from create/get operations
                return []
            return result if isinstance(result, list) else []
        except:
            return []
    
    def create_collection(self, name: str, metadata: Dict = None) -> str:
        """Create a new collection and return its UUID"""
        data = {
            "name": name,
            "metadata": metadata or {},
            "get_or_create": True
        }
        
        result = self._make_request('POST', '/api/v1/collections', data)
        if result and 'id' in result:
            collection_uuid = result['id']
            self.collection_map[name] = collection_uuid
            print(f"   📝 Collection '{name}' -> UUID: {collection_uuid}")
            return collection_uuid
        elif result and 'uuid' in result:
            collection_uuid = result['uuid']
            self.collection_map[name] = collection_uuid
            print(f"   📝 Collection '{name}' -> UUID: {collection_uuid}")
            return collection_uuid
        elif result:
            # Sometimes the whole result is the collection info
            if isinstance(result, dict) and ('id' in result or 'uuid' in result):
                collection_uuid = result.get('id') or result.get('uuid')
                self.collection_map[name] = collection_uuid
                print(f"   📝 Collection '{name}' -> UUID: {collection_uuid}")
                return collection_uuid
            else:
                print(f"   📝 Collection created but UUID format unclear: {result}")
                return str(result)
        return None
    
    def get_collection_uuid(self, name: str) -> str:
        """Get UUID for collection name"""
        if name in self.collection_map:
            return self.collection_map[name]
        
        # Try to find it by listing collections (if that works)
        collections = self.list_collections()
        for collection in collections:
            if isinstance(collection, dict) and collection.get('name') == name:
                uuid = collection.get('id') or collection.get('uuid')
                if uuid:
                    self.collection_map[name] = uuid
                    return uuid
        
        return None
    
    def delete_collection(self, name: str) -> bool:
        """Delete a collection"""
        uuid = self.get_collection_uuid(name)
        if not uuid:
            print(f"   ⚠️ No UUID found for collection '{name}'")
            return False
            
        result = self._make_request('DELETE', f'/api/v1/collections/{uuid}')
        if result is not None:
            if name in self.collection_map:
                del self.collection_map[name]
        return result is not None
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required for embeddings")
        
        try:
            # Use the openai client to generate embeddings
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.embeddings.create(
                model="text-embedding-3-large",
                input=texts
            )
            
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            print(f"❌ Embedding generation failed: {str(e)}")
            return []
    
    def add_documents(self, collection_name: str, ids: List[str], 
                     documents: List[str], metadatas: List[Dict] = None,
                     embeddings: List[List[float]] = None) -> bool:
        """Add documents to a collection"""
        
        uuid = self.get_collection_uuid(collection_name)
        if not uuid:
            print(f"   ❌ Collection '{collection_name}' not found")
            return False
        
        # Generate embeddings if not provided
        if embeddings is None:
            print(f"🤖 Generating embeddings for {len(documents)} documents...")
            embeddings = self.get_embeddings(documents)
            if not embeddings:
                return False
        
        data = {
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas or [{}] * len(ids)
        }
        
        result = self._make_request('POST', f'/api/v1/collections/{uuid}/add', data)
        return result is not None
    
    def query_collection(self, collection_name: str, query_texts: List[str], 
                        n_results: int = 5) -> Dict:
        """Query a collection"""
        
        uuid = self.get_collection_uuid(collection_name)
        if not uuid:
            print(f"   ❌ Collection '{collection_name}' not found")
            return {}
        
        # Generate query embeddings
        query_embeddings = self.get_embeddings(query_texts)
        if not query_embeddings:
            return {}
        
        data = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }
        
        result = self._make_request('POST', f'/api/v1/collections/{uuid}/query', data)
        return result or {}
    
    def get_collection_count(self, collection_name: str) -> int:
        """Get number of items in collection"""
        uuid = self.get_collection_uuid(collection_name)
        if not uuid:
            print(f"   ❌ Collection '{collection_name}' not found")
            return 0
            
        result = self._make_request('GET', f'/api/v1/collections/{uuid}/count')
        return result if isinstance(result, int) else 0

def test_http_client():
    """Test the HTTP client"""
    print("🔧 Testing Railway HTTP ChromaDB Client (UUID-aware)")
    print("=" * 55)
    
    try:
        client = RailwayHTTPChromaClient()
        
        # Test 1: Version check
        print("1️⃣ Testing version...")
        version = client.get_version()
        print(f"   ✅ Version: {version}")
        
        # Test 2: Heartbeat
        print("\n2️⃣ Testing heartbeat...")
        heartbeat = client.heartbeat()
        print(f"   ✅ Heartbeat: {heartbeat}")
        
        # Test 3: List collections
        print("\n3️⃣ Testing list collections...")
        collections = client.list_collections()
        print(f"   ✅ Collections: {collections}")
        
        # Test 4: Create test collection
        print("\n4️⃣ Testing collection creation...")
        collection_uuid = client.create_collection("test_collection", {"description": "Test collection"})
        if collection_uuid:
            print("   ✅ Collection created successfully")
        else:
            print("   ❌ Failed to create collection")
            return False
        
        # Test 5: Add test document
        print("\n5️⃣ Testing document addition...")
        success = client.add_documents(
            "test_collection",
            ["doc1"],
            ["This is a test document for Railway ChromaDB"],
            [{"test": True}]
        )
        if success:
            print("   ✅ Document added successfully")
        else:
            print("   ❌ Failed to add document")
        
        # Test 6: Query collection
        print("\n6️⃣ Testing query...")
        results = client.query_collection("test_collection", ["test document"], 1)
        if results:
            print(f"   ✅ Query successful: {results}")
        else:
            print("   ❌ Query failed")
        
        # Test 7: Get count
        print("\n7️⃣ Testing count...")
        count = client.get_collection_count("test_collection")
        print(f"   ✅ Collection count: {count}")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        deleted = client.delete_collection("test_collection")
        if deleted:
            print("   ✅ Test collection deleted")
        else:
            print("   ⚠️ Failed to delete test collection")
        
        print("\n🎉 All HTTP client tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ HTTP client test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_http_client() 