#!/usr/bin/env python3
"""
Final script to upload feature and screenshot embeddings to Railway ChromaDB
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
        elif result:
            print(f"   📝 Collection response: {result}")
            return str(result.get('id', 'unknown'))
        return None
    
    def get_collection_uuid(self, name: str) -> str:
        """Get UUID for collection name"""
        return self.collection_map.get(name)
    
    def add_documents_batch(self, collection_name: str, ids: List[str], 
                           documents: List[str], metadatas: List[Dict],
                           embeddings: List[List[float]]) -> bool:
        """Add documents to a collection in batch"""
        
        uuid = self.get_collection_uuid(collection_name)
        if not uuid:
            print(f"   ❌ Collection '{collection_name}' not found")
            return False
        
        data = {
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas
        }
        
        result = self._make_request('POST', f'/api/v1/collections/{uuid}/add', data)
        return result is not None
    
    def query_collection(self, collection_name: str, query_embeddings: List[List[float]], 
                        n_results: int = 5) -> Dict:
        """Query a collection with pre-computed embeddings"""
        
        uuid = self.get_collection_uuid(collection_name)
        if not uuid:
            print(f"   ❌ Collection '{collection_name}' not found")
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
            return 0
            
        result = self._make_request('GET', f'/api/v1/collections/{uuid}/count')
        return result if isinstance(result, int) else 0

def upload_to_railway():
    """Upload feature and screenshot embeddings to Railway ChromaDB"""
    print("🚀 Starting Railway ChromaDB Upload")
    print("=" * 50)
    
    try:
        # Initialize client
        client = RailwayHTTPChromaClient()
        
        # Create collections
        print("\n📁 Creating collections...")
        features_uuid = client.create_collection(
            "game_features", 
            {
                "description": "Game feature embeddings",
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat()
            }
        )
        
        screenshots_uuid = client.create_collection(
            "game_screenshots",
            {
                "description": "Game screenshot embeddings", 
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat()
            }
        )
        
        if not features_uuid or not screenshots_uuid:
            print("❌ Failed to create collections")
            return False
        
        # Upload features
        print("\n📊 Uploading feature embeddings...")
        features_file = Path("ChromaDB/feature_embeddings.json")
        if features_file.exists():
            with open(features_file, 'r', encoding='utf-8') as f:
                features_data = json.load(f)
            
            features = features_data.get('features', [])
            print(f"   Found {len(features)} features in file")
            
            # Process in batches
            batch_size = 50
            total_uploaded = 0
            
            for i in range(0, len(features), batch_size):
                batch = features[i:i + batch_size]
                
                ids = []
                embeddings = []
                documents = []
                metadatas = []
                
                for feature in batch:
                    if not feature.get('success', False) or not feature.get('embedding'):
                        continue
                    
                    ids.append(f"feature_{feature['feature_id']}")
                    embeddings.append(feature['embedding'])
                    documents.append(feature.get('combined_text', ''))
                    
                    metadata = {
                        "type": "feature",
                        "feature_id": str(feature['feature_id']),
                        "name": feature.get('name', ''),
                        "description": feature.get('description', ''),
                        "game_id": feature.get('game_id', ''),
                        "token_count": feature.get('actual_tokens', 0)
                    }
                    metadatas.append(metadata)
                
                if ids:
                    success = client.add_documents_batch(
                        "game_features", ids, documents, metadatas, embeddings
                    )
                    if success:
                        total_uploaded += len(ids)
                        print(f"   ✅ Uploaded batch {i//batch_size + 1}: {len(ids)} features")
                    else:
                        print(f"   ❌ Failed to upload batch {i//batch_size + 1}")
            
            print(f"✅ Uploaded {total_uploaded} features")
        else:
            print("⚠️ Feature embeddings file not found")
        
        # Upload screenshots
        print("\n📸 Uploading screenshot embeddings...")
        screenshots_file = Path("ChromaDB/screenshot_embeddings.json")
        if screenshots_file.exists():
            print("   📁 Loading screenshot embeddings (this may take a moment)...")
            with open(screenshots_file, 'r', encoding='utf-8') as f:
                screenshots_data = json.load(f)
            
            screenshots = screenshots_data.get('screenshots', [])
            print(f"   Found {len(screenshots)} screenshots in file")
            
            # Process in smaller batches for screenshots
            batch_size = 25
            total_uploaded = 0
            
            for i in range(0, len(screenshots), batch_size):
                batch = screenshots[i:i + batch_size]
                
                ids = []
                embeddings = []
                documents = []
                metadatas = []
                
                for screenshot in batch:
                    if not screenshot.get('success', False) or not screenshot.get('embedding'):
                        continue
                    
                    ids.append(f"screenshot_{screenshot['screenshot_id']}")
                    embeddings.append(screenshot['embedding'])
                    documents.append(screenshot.get('combined_text', ''))
                    
                    metadata = {
                        "type": "screenshot",
                        "screenshot_id": str(screenshot['screenshot_id']),
                        "path": screenshot.get('path', ''),
                        "caption": screenshot.get('caption', ''),
                        "description": screenshot.get('description', ''),
                        "game_id": screenshot.get('game_id', ''),
                        "token_count": screenshot.get('actual_tokens', 0)
                    }
                    metadatas.append(metadata)
                
                if ids:
                    success = client.add_documents_batch(
                        "game_screenshots", ids, documents, metadatas, embeddings
                    )
                    if success:
                        total_uploaded += len(ids)
                        print(f"   ✅ Uploaded batch {i//batch_size + 1}: {len(ids)} screenshots")
                    else:
                        print(f"   ❌ Failed to upload batch {i//batch_size + 1}")
            
            print(f"✅ Uploaded {total_uploaded} screenshots")
        else:
            print("⚠️ Screenshot embeddings file not found")
        
        # Test the uploaded data
        print("\n🔍 Testing uploaded data...")
        
        # Check counts
        feature_count = client.get_collection_count("game_features")
        screenshot_count = client.get_collection_count("game_screenshots")
        
        print(f"📊 Final counts:")
        print(f"   - Features: {feature_count}")
        print(f"   - Screenshots: {screenshot_count}")
        
        # Test search functionality
        if feature_count > 0:
            print("\n🔍 Testing feature search...")
            # Generate a test query embedding
            openai_client = openai.OpenAI(api_key=client.openai_api_key)
            test_embedding = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=["building construction gameplay"]
            ).data[0].embedding
            
            results = client.query_collection("game_features", [test_embedding], 3)
            if results and results.get('ids'):
                print(f"   ✅ Feature search works! Found {len(results['ids'][0])} results")
                for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
                    print(f"      {i+1}. {doc_id} (distance: {distance:.4f})")
            else:
                print("   ⚠️ Feature search returned no results")
        
        if screenshot_count > 0:
            print("\n🔍 Testing screenshot search...")
            # Generate a test query embedding
            test_embedding = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=["game interface menu screen"]
            ).data[0].embedding
            
            results = client.query_collection("game_screenshots", [test_embedding], 3)
            if results and results.get('ids'):
                print(f"   ✅ Screenshot search works! Found {len(results['ids'][0])} results")
                for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
                    print(f"      {i+1}. {doc_id} (distance: {distance:.4f})")
            else:
                print("   ⚠️ Screenshot search returned no results")
        
        print("\n🎉 Upload completed successfully!")
        print(f"🌐 Your ChromaDB is now available at: {client.base_url}")
        print("✅ You can now use your Railway ChromaDB service for semantic search!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Upload failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    upload_to_railway() 