#!/usr/bin/env python3
"""
Script to connect to Railway ChromaDB service and upload local database
"""

import os
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import urllib.parse

class RailwayChromaDBManager:
    def __init__(self):
        # Load environment variables
        load_dotenv('.env.local')
        
        # Get Railway ChromaDB credentials
        self.chroma_url = os.getenv("CHROMA_PUBLIC_URL")
        self.chroma_token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
        
        if not self.chroma_url or not self.chroma_token:
            raise ValueError("Missing CHROMA_PUBLIC_URL or CHROMA_SERVER_AUTHN_CREDENTIALS in environment variables")
        
        print(f"Connecting to ChromaDB at: {self.chroma_url}")
        
        # Initialize ChromaDB HttpClient for Railway
        # Parse the URL to extract host and port
        parsed_url = urllib.parse.urlparse(self.chroma_url)
        host = parsed_url.netloc or parsed_url.path.strip('/')
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        ssl = parsed_url.scheme == 'https'
        
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            ssl=ssl,
            headers={"Authorization": f"Bearer {self.chroma_token}"}
        )
        
        # Set up OpenAI embedding function
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("Missing OPENAI_API_KEY in environment variables")
            
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-large"
        )
        
        print("✅ ChromaDB client initialized successfully")
    
    def test_connection(self):
        """Test the connection to Railway ChromaDB"""
        try:
            # Try to list collections
            collections = self.client.list_collections()
            print(f"✅ Connection successful! Found {len(collections)} collections:")
            for collection in collections:
                print(f"  - {collection.name}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False
    
    def create_collections(self):
        """Create collections for features and screenshots"""
        try:
            # Features collection
            features_collection = self.client.get_or_create_collection(
                name="game_features",
                metadata={
                    "description": "Game feature embeddings",
                    "embedding_model": "text-embedding-3-large",
                    "created_at": datetime.now().isoformat(),
                    "hnsw:space": "cosine"
                },
                embedding_function=self.embedding_function
            )
            print("✅ Features collection created/retrieved")
            
            # Screenshots collection
            screenshots_collection = self.client.get_or_create_collection(
                name="game_screenshots",
                metadata={
                    "description": "Game screenshot embeddings",
                    "embedding_model": "text-embedding-3-large",
                    "created_at": datetime.now().isoformat(),
                    "hnsw:space": "cosine"
                },
                embedding_function=self.embedding_function
            )
            print("✅ Screenshots collection created/retrieved")
            
            return features_collection, screenshots_collection
            
        except Exception as e:
            print(f"❌ Error creating collections: {str(e)}")
            return None, None
    
    def upload_feature_embeddings(self, json_file="ChromaDB/feature_embeddings.json"):
        """Upload feature embeddings from JSON file to Railway ChromaDB"""
        if not Path(json_file).exists():
            print(f"❌ Feature embeddings file not found: {json_file}")
            return 0
            
        print(f"📁 Loading feature embeddings from {json_file}...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        features = data.get('features', [])
        print(f"📊 Found {len(features)} features in JSON file")
        
        collection = self.client.get_or_create_collection(
            name="game_features",
            embedding_function=self.embedding_function
        )
        
        # Check current count
        current_count = collection.count()
        print(f"📊 Current features in database: {current_count}")
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for feature in features:
            if not feature.get('success', False) or not feature.get('embedding'):
                continue
                
            feature_id = f"feature_{feature['feature_id']}"
            ids.append(feature_id)
            embeddings.append(feature['embedding'])
            documents.append(feature.get('combined_text', ''))
            
            # Enhanced metadata
            metadata = {
                "type": "feature",
                "feature_id": str(feature['feature_id']),
                "name": feature.get('name', ''),
                "description": feature.get('description', ''),
                "game_id": feature.get('game_id', ''),
                "token_count": feature.get('actual_tokens', 0),
                "created_at": data.get('metadata', {}).get('generated_at', ''),
                "content_hash": feature.get('content_hash', ''),
                "embedding_generated_at": feature.get('embedding_generated_at', ''),
                "last_updated": feature.get('updated_at', feature.get('created_at', '')),
                "embedding_dimensions": len(feature.get('embedding', [])),
                "model": feature.get('model', 'text-embedding-3-large'),
                "processing_success": feature.get('success', False)
            }
            
            # Only include non-None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            metadatas.append(metadata)
        
        # Upload in batches
        batch_size = 100
        total_added = 0
        
        print(f"🚀 Uploading {len(ids)} features in batches of {batch_size}...")
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                collection.upsert(  # Use upsert to handle duplicates
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
                print(f"✅ Uploaded batch {i//batch_size + 1}: {len(batch_ids)} features")
            except Exception as e:
                print(f"❌ Error uploading batch {i//batch_size + 1}: {str(e)}")
        
        print(f"✅ Successfully uploaded {total_added} feature embeddings to Railway ChromaDB")
        return total_added
    
    def upload_screenshot_embeddings(self, json_file="ChromaDB/screenshot_embeddings.json"):
        """Upload screenshot embeddings from JSON file to Railway ChromaDB"""
        if not Path(json_file).exists():
            print(f"❌ Screenshot embeddings file not found: {json_file}")
            return 0
            
        print(f"📁 Loading screenshot embeddings from {json_file}...")
        print("⚠️  Note: This is a large file (118MB), this may take a while...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        screenshots = data.get('screenshots', [])
        print(f"📊 Found {len(screenshots)} screenshots in JSON file")
        
        collection = self.client.get_or_create_collection(
            name="game_screenshots",
            embedding_function=self.embedding_function
        )
        
        # Check current count
        current_count = collection.count()
        print(f"📊 Current screenshots in database: {current_count}")
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for screenshot in screenshots:
            if not screenshot.get('success', False) or not screenshot.get('embedding'):
                continue
                
            screenshot_id = f"screenshot_{screenshot['screenshot_id']}"
            ids.append(screenshot_id)
            embeddings.append(screenshot['embedding'])
            documents.append(screenshot.get('combined_text', ''))
            
            # Enhanced metadata
            metadata = {
                "type": "screenshot",
                "screenshot_id": str(screenshot['screenshot_id']),
                "path": screenshot.get('path', ''),
                "caption": screenshot.get('caption', ''),
                "description": screenshot.get('description', ''),
                "game_id": screenshot.get('game_id', ''),
                "token_count": screenshot.get('actual_tokens', 0),
                "capture_time": screenshot.get('capture_time', ''),
                "created_at": data.get('metadata', {}).get('generated_at', ''),
                "content_hash": screenshot.get('content_hash', ''),
                "embedding_generated_at": screenshot.get('embedding_generated_at', ''),
                "last_updated": screenshot.get('updated_at', screenshot.get('created_at', screenshot.get('capture_time', ''))),
                "embedding_dimensions": len(screenshot.get('embedding', [])),
                "model": screenshot.get('model', 'text-embedding-3-large'),
                "processing_success": screenshot.get('success', False)
            }
            
            # Only include non-None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            metadatas.append(metadata)
        
        # Upload in batches
        batch_size = 50  # Smaller batches for screenshots due to larger data
        total_added = 0
        
        print(f"🚀 Uploading {len(ids)} screenshots in batches of {batch_size}...")
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                collection.upsert(  # Use upsert to handle duplicates
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
                print(f"✅ Uploaded batch {i//batch_size + 1}: {len(batch_ids)} screenshots")
            except Exception as e:
                print(f"❌ Error uploading batch {i//batch_size + 1}: {str(e)}")
        
        print(f"✅ Successfully uploaded {total_added} screenshot embeddings to Railway ChromaDB")
        return total_added
    
    def test_search(self):
        """Test search functionality on uploaded data"""
        print("\n🔍 Testing search functionality...")
        
        try:
            # Test feature search
            features_collection = self.client.get_collection("game_features")
            feature_count = features_collection.count()
            print(f"📊 Features collection has {feature_count} items")
            
            if feature_count > 0:
                print("\n🔍 Testing feature search with query: 'building construction'")
                results = features_collection.query(
                    query_texts=["building construction"],
                    n_results=3
                )
                
                print("📋 Feature search results:")
                for i, (doc_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0], results['documents'][0], 
                    results['metadatas'][0], results['distances'][0]
                )):
                    print(f"  {i+1}. ID: {doc_id}")
                    print(f"     Distance: {distance:.4f}")
                    print(f"     Name: {metadata.get('name', 'N/A')}")
                    print(f"     Document: {document[:100]}...")
                    print()
            
            # Test screenshot search
            screenshots_collection = self.client.get_collection("game_screenshots")
            screenshot_count = screenshots_collection.count()
            print(f"📊 Screenshots collection has {screenshot_count} items")
            
            if screenshot_count > 0:
                print("\n🔍 Testing screenshot search with query: 'game interface menu'")
                results = screenshots_collection.query(
                    query_texts=["game interface menu"],
                    n_results=3
                )
                
                print("📋 Screenshot search results:")
                for i, (doc_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0], results['documents'][0], 
                    results['metadatas'][0], results['distances'][0]
                )):
                    print(f"  {i+1}. ID: {doc_id}")
                    print(f"     Distance: {distance:.4f}")
                    print(f"     Path: {metadata.get('path', 'N/A')}")
                    print(f"     Caption: {metadata.get('caption', 'N/A')}")
                    print(f"     Document: {document[:100]}...")
                    print()
            
            return True
            
        except Exception as e:
            print(f"❌ Search test failed: {str(e)}")
            return False
    
    def get_database_info(self):
        """Get database statistics"""
        print("\n📊 Database Information:")
        try:
            collections = self.client.list_collections()
            for collection in collections:
                count = collection.count()
                print(f"  - {collection.name}: {count} items")
            return True
        except Exception as e:
            print(f"❌ Error getting database info: {str(e)}")
            return False

def main():
    """Main function to upload and test ChromaDB on Railway"""
    print("🚀 Starting Railway ChromaDB Upload and Test Script")
    print("=" * 50)
    
    try:
        # Initialize manager
        manager = RailwayChromaDBManager()
        
        # Test connection
        if not manager.test_connection():
            print("❌ Failed to connect to Railway ChromaDB. Please check your environment variables.")
            return
        
        # Create collections
        features_collection, screenshots_collection = manager.create_collections()
        if not features_collection or not screenshots_collection:
            print("❌ Failed to create collections.")
            return
        
        # Get initial database info
        manager.get_database_info()
        
        # Upload features
        print("\n" + "=" * 50)
        feature_count = manager.upload_feature_embeddings()
        
        # Upload screenshots (this will take longer)
        print("\n" + "=" * 50)
        screenshot_count = manager.upload_screenshot_embeddings()
        
        # Test search functionality
        print("\n" + "=" * 50)
        manager.test_search()
        
        # Final database info
        print("\n" + "=" * 50)
        manager.get_database_info()
        
        print("\n✅ Upload and testing completed successfully!")
        print(f"📊 Total uploaded: {feature_count} features, {screenshot_count} screenshots")
        
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 