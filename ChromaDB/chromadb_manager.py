import os
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import urllib.parse

class ChromaDBManager:
    def __init__(self, db_path="./ChromaDB/chroma_db", use_openai_embeddings=True):
        # Import config to get ChromaDB settings
        from utils.config import get_chroma_config
        chroma_config = get_chroma_config()
        
        if chroma_config["is_railway"] and chroma_config["host"]:
            # Railway environment - use HTTP client
            print(f"Connecting to Railway ChromaDB at {chroma_config['host']}")
            
            # Parse the URL to extract components
            parsed_url = urllib.parse.urlparse(chroma_config['host'])
            host = parsed_url.hostname or parsed_url.netloc
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            ssl = parsed_url.scheme == 'https'
            
            # Create settings for Railway ChromaDB
            settings = Settings(
                chroma_api_impl="chromadb.api.fastapi.FastAPI",
                chroma_server_host=host,
                chroma_server_http_port=port,
                chroma_server_ssl_enabled=ssl,
                chroma_server_headers={"Authorization": f"Bearer {chroma_config['auth_token']}"} if chroma_config['auth_token'] else {}
            )
            
            # Initialize HTTP client for Railway
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                ssl=ssl,
                headers={"Authorization": f"Bearer {chroma_config['auth_token']}"} if chroma_config['auth_token'] else {},
                settings=settings
            )
            self.db_path = None  # No local path in Railway
        else:
            # Local environment - use persistent client
            self.db_path = Path(db_path)
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            print(f"ChromaDB initialized at {self.db_path}")
        
        # Set up embedding function for search consistency
        self.embedding_function = None
        if use_openai_embeddings:
            load_dotenv('.env.local')
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                # Use same model as embedding generation
                self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=openai_api_key,
                    model_name="text-embedding-3-large"
                )
    
    def create_collections(self):
        """Create collections for features and screenshots"""
        # Features collection with cosine distance for better text similarity
        features_collection = self.client.get_or_create_collection(
            name="game_features",
            metadata={
                "description": "Game feature embeddings",
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat(),
                "hnsw:space": "cosine"  # Use cosine distance for better text semantics
            },
            embedding_function=self.embedding_function
        )
        
        # Screenshots collection with cosine distance for better text similarity
        screenshots_collection = self.client.get_or_create_collection(
            name="game_screenshots",
            metadata={
                "description": "Game screenshot embeddings",
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat(),
                "hnsw:space": "cosine"  # Use cosine distance for better text semantics
            },
            embedding_function=self.embedding_function
        )
        
        return features_collection, screenshots_collection
    
    def load_feature_embeddings_from_json(self, json_file):
        """Load feature embeddings from JSON file into ChromaDB with enhanced metadata"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        features = data.get('features', [])
        
        collection = self.client.get_or_create_collection(
            name="game_features",
            embedding_function=self.embedding_function
        )
        
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
            
            # Enhanced metadata for change detection and tracking
            metadata = {
                "type": "feature",
                "feature_id": str(feature['feature_id']),
                "name": feature.get('name', ''),
                "description": feature.get('description', ''),
                "game_id": feature.get('game_id', ''),
                "token_count": feature.get('actual_tokens', 0),
                "created_at": data.get('metadata', {}).get('generated_at', ''),
                
                # Enhanced fields for change detection
                "content_hash": feature.get('content_hash', ''),
                "embedding_generated_at": feature.get('embedding_generated_at', ''),
                "last_updated": feature.get('updated_at', feature.get('created_at', '')),
                "embedding_dimensions": feature.get('embedding_dimension', len(feature.get('embedding', []))),
                "model": feature.get('model', 'text-embedding-3-large'),
                "custom_dimensions": feature.get('dimensions'),
                
                # Processing metadata
                "generation_attempts": feature.get('attempts', 1),
                "token_breakdown": str(feature.get('token_breakdown', {})),  # Convert dict to string for ChromaDB
                "actual_tokens": feature.get('actual_tokens', 0),
                "processing_success": feature.get('success', False)
            }
            
            # Only include non-None values in metadata (ChromaDB doesn't like None values)
            metadata = {k: v for k, v in metadata.items() if v is not None}
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
                print(f"Added batch {i//batch_size + 1}: {len(batch_ids)} features")
            except Exception as e:
                print(f"Error adding batch {i//batch_size + 1}: {str(e)}")
                # Try to add individually to identify problematic features
                for j, (feature_id, embedding, document, metadata) in enumerate(zip(batch_ids, batch_embeddings, batch_documents, batch_metadatas)):
                    try:
                        collection.add(
                            ids=[feature_id],
                            embeddings=[embedding],
                            documents=[document],
                            metadatas=[metadata]
                        )
                        total_added += 1
                    except Exception as individual_error:
                        print(f"Failed to add feature {feature_id}: {str(individual_error)}")
        
        print(f"Successfully loaded {total_added} feature embeddings with enhanced metadata")
        return total_added
    
    def load_screenshot_embeddings_from_json(self, json_file):
        """Load screenshot embeddings from JSON file into ChromaDB with enhanced metadata"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        screenshots = data.get('screenshots', [])
        
        collection = self.client.get_or_create_collection(
            name="game_screenshots",
            embedding_function=self.embedding_function
        )
        
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
            
            # Enhanced metadata for change detection and tracking
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
                
                # Enhanced fields for change detection
                "content_hash": screenshot.get('content_hash', ''),
                "embedding_generated_at": screenshot.get('embedding_generated_at', ''),
                "last_updated": screenshot.get('updated_at', screenshot.get('created_at', screenshot.get('capture_time', ''))),
                "embedding_dimensions": screenshot.get('embedding_dimension', len(screenshot.get('embedding', []))),
                "model": screenshot.get('model', 'text-embedding-3-large'),
                "custom_dimensions": screenshot.get('dimensions'),
                
                # Processing metadata
                "generation_attempts": screenshot.get('attempts', 1),
                "token_breakdown": str(screenshot.get('token_breakdown', {})),  # Convert dict to string for ChromaDB
                "actual_tokens": screenshot.get('actual_tokens', 0),
                "processing_success": screenshot.get('success', False),
                
                # Screenshot-specific metadata
                "elements_data": str(screenshot.get('elements', '')),  # Store elements data for reference
            }
            
            # Only include non-None values in metadata (ChromaDB doesn't like None values)
            metadata = {k: v for k, v in metadata.items() if v is not None}
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        total_added = 0
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            try:
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
                print(f"Added batch {i//batch_size + 1}: {len(batch_ids)} screenshots")
            except Exception as e:
                print(f"Error adding batch {i//batch_size + 1}: {str(e)}")
                # Try to add individually to identify problematic screenshots
                for j, (screenshot_id, embedding, document, metadata) in enumerate(zip(batch_ids, batch_embeddings, batch_documents, batch_metadatas)):
                    try:
                        collection.add(
                            ids=[screenshot_id],
                            embeddings=[embedding],
                            documents=[document],
                            metadatas=[metadata]
                        )
                        total_added += 1
                    except Exception as individual_error:
                        print(f"Failed to add screenshot {screenshot_id}: {str(individual_error)}")
        
        print(f"Successfully loaded {total_added} screenshot embeddings with enhanced metadata")
        return total_added
    
    def search_features(self, query, n_results=5, game_id=None, feature_ids=None):
        """Search for similar features"""
        collection = self.client.get_collection(
            "game_features", 
            embedding_function=self.embedding_function
        )
        
        # Build where clause for filtering
        where_conditions = []
        
        if game_id:
            where_conditions.append({"game_id": game_id})
        
        if feature_ids:
            # Convert feature_ids to strings if they aren't already
            str_feature_ids = [str(fid) for fid in feature_ids]
            where_conditions.append({"feature_id": {"$in": str_feature_ids}})
        
        # Combine conditions with $and if multiple exist
        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause
        )
        
        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            formatted_results.append({
                'id': doc_id,
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            })
        
        return formatted_results
    
    def search_screenshots(self, query, n_results=5, game_id=None, screenshot_ids=None):
        """Search for similar screenshots"""
        collection = self.client.get_collection(
            "game_screenshots", 
            embedding_function=self.embedding_function
        )
        
        # Build where clause for filtering
        where_conditions = []
        
        if game_id:
            where_conditions.append({"game_id": game_id})
        
        if screenshot_ids:
            # Convert screenshot_ids to strings if they aren't already
            str_screenshot_ids = [str(sid) for sid in screenshot_ids]
            where_conditions.append({"screenshot_id": {"$in": str_screenshot_ids}})
        
        # Combine conditions with $and if multiple exist
        where_clause = None
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause
        )
        
        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            formatted_results.append({
                'id': doc_id,
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            })
        
        return formatted_results
    
    def get_database_info(self):
        """Get database statistics"""
        collections = []
        for collection_name in ["game_features", "game_screenshots"]:
            try:
                collection = self.client.get_collection(collection_name)
                collections.append({
                    "name": collection_name,
                    "count": collection.count()
                })
            except:
                collections.append({
                    "name": collection_name,
                    "count": 0
                })
        
        # Import config to check environment
        from utils.config import get_environment
        
        return {
            "database_path": str(self.db_path) if self.db_path else f"Railway ChromaDB ({get_environment()})",
            "collections": collections
        } 