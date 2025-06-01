import os
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class ChromaDBManager:
    def __init__(self, db_path="./ChromaDB/chroma_db", use_openai_embeddings=True):
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
        
        print(f"ChromaDB initialized at {self.db_path}")
    
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
        """Load feature embeddings from JSON file into ChromaDB"""
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
            
            metadata = {
                "type": "feature",
                "feature_id": str(feature['feature_id']),
                "name": feature.get('name', ''),
                "description": feature.get('description', ''),
                "game_id": feature.get('game_id', ''),
                "token_count": feature.get('actual_tokens', 0),
                "created_at": data.get('metadata', {}).get('generated_at', '')
            }
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        
        return len(ids)
    
    def load_screenshot_embeddings_from_json(self, json_file):
        """Load screenshot embeddings from JSON file into ChromaDB"""
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
            
            metadata = {
                "type": "screenshot",
                "screenshot_id": str(screenshot['screenshot_id']),
                "path": screenshot.get('path', ''),
                "caption": screenshot.get('caption', ''),
                "game_id": screenshot.get('game_id', ''),
                "token_count": screenshot.get('actual_tokens', 0),
                "capture_time": screenshot.get('capture_time', ''),
                "created_at": data.get('metadata', {}).get('generated_at', '')
            }
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        
        return len(ids)
    
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
        
        return {
            "database_path": str(self.db_path),
            "collections": collections
        } 