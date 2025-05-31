# ChromaDB Vector Database Integration Guide

## Overview
This guide provides step-by-step instructions for integrating a ChromaDB vector database system with automatic feature and screenshot embedding generation into an existing agent project. The system enables semantic search across game features and screenshots using OpenAI embeddings.

## Prerequisites
- Python 3.8+
- PostgreSQL database with game data
- OpenAI API key
- Access to environment variables (.env.local file)

## Required Dependencies

### 1. Install Core Dependencies
```bash
pip install chromadb>=0.4.15
pip install openai>=1.0.0
pip install pg8000
pip install python-dotenv
pip install pathlib
```

### 2. Environment Setup
Create or update `.env.local` file with required variables:
```
PG_USER=your_postgres_user
PG_PASSWORD=your_postgres_password
PG_HOST=your_postgres_host
PG_PORT=5432
PG_DATABASE=your_database_name
OPENAI_API_KEY=your_openai_api_key
```

## Integration Steps

### Phase 1: Database Schema Requirements

#### Step 1: Verify Database Tables
Ensure your PostgreSQL database has these tables with required fields:

**features_game table:**
- `feature_id` (primary key)
- `name` (text)
- `description` (text)
- `game_id` (UUID/text)

**screenshots table:**
- `screenshot_id` (primary key)
- `path` (text file path)
- `game_id` (UUID/text)
- `caption` (text)
- `description` (text)
- `elements` (JSONB - UI elements data)
- `capture_time` (timestamp)

#### Step 2: Create Database Connection Helper
```python
# utils/database_connection.py
import pg8000.dbapi
import os
from dotenv import load_dotenv

class DatabaseConnection:
    def __init__(self):
        load_dotenv('.env.local')
        self.conn = pg8000.dbapi.connect(
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE")
        )
    
    def get_connection(self):
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
```

### Phase 2: Feature Embedding Generation

#### Step 3: Create Feature Embeddings Generator
```python
# embeddings/feature_embeddings_generator.py
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from utils.database_connection import DatabaseConnection

class FeatureEmbeddingsGenerator:
    def __init__(self):
        self.db = DatabaseConnection()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def query_features_from_database(self, limit=None, game_id=None):
        """Query features from PostgreSQL database"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if game_id:
            query = """
                SELECT feature_id, name, description, game_id 
                FROM features_game 
                WHERE game_id = %s
                ORDER BY feature_id
            """
            params = (game_id,)
        else:
            query = """
                SELECT feature_id, name, description, game_id 
                FROM features_game 
                ORDER BY feature_id
            """
            params = ()
            
        if limit:
            query += " LIMIT %s"
            params = params + (limit,)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        features = []
        for row in results:
            feature_id, name, description, game_id = row
            features.append({
                "feature_id": feature_id,
                "name": name or "",
                "description": description or "",
                "game_id": str(game_id) if game_id else ""
            })
        
        return features
    
    def combine_feature_text(self, feature):
        """Combine name and description for embedding"""
        text_parts = []
        if feature.get("name"):
            text_parts.append(feature["name"])
        if feature.get("description"):
            text_parts.append(feature["description"])
        return " - ".join(text_parts)
    
    def generate_embedding_for_text(self, text):
        """Generate OpenAI embedding for text"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                encoding_format="float"
            )
            
            return {
                "embedding": response.data[0].embedding,
                "success": True,
                "tokens": response.usage.total_tokens,
                "model": "text-embedding-3-large"
            }
        except Exception as e:
            return {
                "embedding": [],
                "success": False,
                "error": str(e)
            }
    
    def generate_all_feature_embeddings(self, limit=None, game_id=None):
        """Generate embeddings for all features"""
        features = self.query_features_from_database(limit, game_id)
        
        embeddings_data = {
            "metadata": {
                "total_features": len(features),
                "model": "text-embedding-3-large",
                "generated_at": datetime.now().isoformat()
            },
            "features": []
        }
        
        total_tokens = 0
        
        for feature in features:
            combined_text = self.combine_feature_text(feature)
            embedding_result = self.generate_embedding_for_text(combined_text)
            
            feature_data = {
                **feature,
                "combined_text": combined_text,
                "embedding": embedding_result["embedding"],
                "success": embedding_result["success"],
                "model": embedding_result.get("model", ""),
                "actual_tokens": embedding_result.get("tokens", 0)
            }
            
            if not embedding_result["success"]:
                feature_data["error"] = embedding_result["error"]
            
            embeddings_data["features"].append(feature_data)
            total_tokens += embedding_result.get("tokens", 0)
        
        embeddings_data["metadata"]["total_tokens"] = total_tokens
        return embeddings_data
    
    def save_embeddings_to_file(self, embeddings_data, output_file):
        """Save embeddings to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
```

#### Step 4: Create Feature Embedding Generation Script
```python
# scripts/generate_feature_embeddings.py
import argparse
from embeddings.feature_embeddings_generator import FeatureEmbeddingsGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate feature embeddings")
    parser.add_argument("--limit", type=int, help="Limit number of features")
    parser.add_argument("--game_id", help="Specific game ID to process")
    parser.add_argument("--output", default="feature_embeddings.json", help="Output filename")
    
    args = parser.parse_args()
    
    generator = FeatureEmbeddingsGenerator()
    embeddings_data = generator.generate_all_feature_embeddings(
        limit=args.limit, 
        game_id=args.game_id
    )
    
    generator.save_embeddings_to_file(embeddings_data, args.output)
    print(f"Feature embeddings saved to {args.output}")
    print(f"Total features: {embeddings_data['metadata']['total_features']}")
    print(f"Total tokens: {embeddings_data['metadata']['total_tokens']}")

if __name__ == "__main__":
    main()
```

### Phase 3: Screenshot Embedding Generation

#### Step 5: Create Screenshot Embeddings Generator
```python
# embeddings/screenshot_embeddings_generator.py
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from utils.database_connection import DatabaseConnection

class ScreenshotEmbeddingsGenerator:
    def __init__(self):
        self.db = DatabaseConnection()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def query_screenshots_from_database(self, limit=None, game_id=None):
        """Query screenshots from PostgreSQL database"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if game_id:
            query = """
                SELECT screenshot_id, path, game_id, caption, elements, description, capture_time
                FROM screenshots 
                WHERE game_id = %s
                ORDER BY capture_time DESC
            """
            params = (game_id,)
        else:
            query = """
                SELECT screenshot_id, path, game_id, caption, elements, description, capture_time
                FROM screenshots 
                ORDER BY capture_time DESC
            """
            params = ()
            
        if limit:
            query += " LIMIT %s"
            params = params + (limit,)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        screenshots = []
        for row in results:
            screenshot_id, path, game_id, caption, elements, description, capture_time = row
            screenshots.append({
                "screenshot_id": str(screenshot_id),
                "path": path or "",
                "game_id": str(game_id) if game_id else "",
                "caption": caption or "",
                "elements": elements,
                "description": description or "",
                "capture_time": capture_time.isoformat() if capture_time else ""
            })
        
        return screenshots
    
    def format_elements_to_text(self, elements_json):
        """Convert JSONB elements to readable text"""
        if not elements_json:
            return ""
            
        try:
            if isinstance(elements_json, (dict, list)):
                elements = elements_json
            else:
                elements = json.loads(elements_json) if isinstance(elements_json, str) else elements_json
            
            if isinstance(elements, list):
                formatted_elements = []
                for element in elements:
                    if isinstance(element, dict):
                        parts = []
                        if element.get('name'):
                            parts.append(f"Element: {element['name']}")
                        if element.get('type'):
                            parts.append(f"Type: {element['type']}")
                        if element.get('description'):
                            parts.append(f"Description: {element['description']}")
                        if parts:
                            formatted_elements.append(" - ".join(parts))
                return "; ".join(formatted_elements)
            elif isinstance(elements, dict):
                parts = []
                if elements.get('name'):
                    parts.append(f"Element: {elements['name']}")
                if elements.get('type'):
                    parts.append(f"Type: {elements['type']}")
                if elements.get('description'):
                    parts.append(f"Description: {elements['description']}")
                return " - ".join(parts)
            else:
                return str(elements)
                
        except (json.JSONDecodeError, TypeError):
            return str(elements_json) if elements_json else ""
    
    def combine_screenshot_text(self, screenshot):
        """Combine caption, description, and elements for embedding"""
        text_parts = []
        
        if screenshot.get("caption"):
            text_parts.append(f"Caption: {screenshot['caption']}")
            
        if screenshot.get("description"):
            text_parts.append(f"Description: {screenshot['description']}")
            
        if screenshot.get("elements"):
            elements_text = self.format_elements_to_text(screenshot["elements"])
            if elements_text:
                text_parts.append(f"UI Elements: {elements_text}")
        
        return " | ".join(text_parts)
    
    def generate_embedding_for_text(self, text):
        """Generate OpenAI embedding for text"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-large",
                input=text,
                encoding_format="float"
            )
            
            return {
                "embedding": response.data[0].embedding,
                "success": True,
                "tokens": response.usage.total_tokens,
                "model": "text-embedding-3-large"
            }
        except Exception as e:
            return {
                "embedding": [],
                "success": False,
                "error": str(e)
            }
    
    def generate_all_screenshot_embeddings(self, limit=None, game_id=None):
        """Generate embeddings for all screenshots"""
        screenshots = self.query_screenshots_from_database(limit, game_id)
        
        embeddings_data = {
            "metadata": {
                "total_screenshots": len(screenshots),
                "model": "text-embedding-3-large",
                "generated_at": datetime.now().isoformat()
            },
            "screenshots": []
        }
        
        total_tokens = 0
        
        for screenshot in screenshots:
            combined_text = self.combine_screenshot_text(screenshot)
            embedding_result = self.generate_embedding_for_text(combined_text)
            
            screenshot_data = {
                **screenshot,
                "combined_text": combined_text,
                "embedding": embedding_result["embedding"],
                "success": embedding_result["success"],
                "model": embedding_result.get("model", ""),
                "actual_tokens": embedding_result.get("tokens", 0)
            }
            
            if not embedding_result["success"]:
                screenshot_data["error"] = embedding_result["error"]
            
            embeddings_data["screenshots"].append(screenshot_data)
            total_tokens += embedding_result.get("tokens", 0)
        
        embeddings_data["metadata"]["total_tokens"] = total_tokens
        return embeddings_data
    
    def save_embeddings_to_file(self, embeddings_data, output_file):
        """Save embeddings to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
```

#### Step 6: Create Screenshot Embedding Generation Script
```python
# scripts/generate_screenshot_embeddings.py
import argparse
from embeddings.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate screenshot embeddings")
    parser.add_argument("--limit", type=int, help="Limit number of screenshots")
    parser.add_argument("--game_id", help="Specific game ID to process")
    parser.add_argument("--output", default="screenshot_embeddings.json", help="Output filename")
    
    args = parser.parse_args()
    
    generator = ScreenshotEmbeddingsGenerator()
    embeddings_data = generator.generate_all_screenshot_embeddings(
        limit=args.limit, 
        game_id=args.game_id
    )
    
    generator.save_embeddings_to_file(embeddings_data, args.output)
    print(f"Screenshot embeddings saved to {args.output}")
    print(f"Total screenshots: {embeddings_data['metadata']['total_screenshots']}")
    print(f"Total tokens: {embeddings_data['metadata']['total_tokens']}")

if __name__ == "__main__":
    main()
```

### Phase 4: ChromaDB Vector Database Setup

#### Step 7: Create ChromaDB Manager
```python
# vector_db/chromadb_manager.py
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
    def __init__(self, db_path="./chroma_db", use_openai_embeddings=True):
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
        # Features collection
        features_collection = self.client.get_or_create_collection(
            name="game_features",
            metadata={
                "description": "Game feature embeddings",
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat()
            },
            embedding_function=self.embedding_function
        )
        
        # Screenshots collection
        screenshots_collection = self.client.get_or_create_collection(
            name="game_screenshots",
            metadata={
                "description": "Game screenshot embeddings",
                "embedding_model": "text-embedding-3-large",
                "created_at": datetime.now().isoformat()
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
                "description": screenshot.get('description', ''),
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
    
    def search_features(self, query, n_results=5, game_id=None):
        """Search for similar features"""
        collection = self.client.get_collection(
            "game_features", 
            embedding_function=self.embedding_function
        )
        
        where_clause = None
        if game_id:
            where_clause = {"game_id": game_id}
        
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
    
    def search_screenshots(self, query, n_results=5, game_id=None):
        """Search for similar screenshots"""
        collection = self.client.get_collection(
            "game_screenshots", 
            embedding_function=self.embedding_function
        )
        
        where_clause = None
        if game_id:
            where_clause = {"game_id": game_id}
        
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
```

### Phase 5: Integration Into Agent Application

#### Step 8: Create Agent Integration Interface
```python
# agent_integration/vector_search_interface.py
from vector_db.chromadb_manager import ChromaDBManager
from typing import List, Dict, Any, Optional

class GameDataSearchInterface:
    """Interface for agent applications to search game data"""
    
    def __init__(self, chroma_db_path="./chroma_db"):
        self.vector_db = ChromaDBManager(
            db_path=chroma_db_path, 
            use_openai_embeddings=True
        )
        
    def search_game_features(self, query: str, limit: int = 5, 
                           game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for game features relevant to query
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            game_id: Optional filter by specific game
            
        Returns:
            List of matching features with metadata
        """
        results = self.vector_db.search_features(query, limit, game_id)
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            formatted_results.append({
                'type': 'feature',
                'name': metadata.get('name', ''),
                'description': metadata.get('description', ''),
                'game_id': metadata.get('game_id', ''),
                'relevance_score': 1 - result['distance'],  # Convert distance to similarity
                'content': result['document']
            })
        
        return formatted_results
    
    def search_game_screenshots(self, query: str, limit: int = 5, 
                              game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for game screenshots relevant to query
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            game_id: Optional filter by specific game
            
        Returns:
            List of matching screenshots with metadata
        """
        results = self.vector_db.search_screenshots(query, limit, game_id)
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            formatted_results.append({
                'type': 'screenshot',
                'path': metadata.get('path', ''),
                'caption': metadata.get('caption', ''),
                'description': metadata.get('description', ''),
                'game_id': metadata.get('game_id', ''),
                'relevance_score': 1 - result['distance'],  # Convert distance to similarity
                'content': result['document']
            })
        
        return formatted_results
    
    def search_all_game_content(self, query: str, limit: int = 10, 
                              game_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both features and screenshots
        
        Returns:
            Dictionary with 'features' and 'screenshots' keys
        """
        features = self.search_game_features(query, limit//2, game_id)
        screenshots = self.search_game_screenshots(query, limit//2, game_id)
        
        return {
            'features': features,
            'screenshots': screenshots
        }
```

#### Step 9: Create Agent Integration Example
```python
# agent_integration/example_agent_usage.py
from agent_integration.vector_search_interface import GameDataSearchInterface

class GameAnalysisAgent:
    """Example agent that uses vector search for game analysis"""
    
    def __init__(self):
        self.search_interface = GameDataSearchInterface()
        
    def analyze_game_theme(self, theme_query: str, game_id: Optional[str] = None):
        """Analyze how a game implements a specific theme"""
        print(f"Analyzing theme: {theme_query}")
        
        # Search for relevant content
        content = self.search_interface.search_all_game_content(
            query=theme_query, 
            limit=10, 
            game_id=game_id
        )
        
        # Process features
        feature_analysis = []
        for feature in content['features']:
            feature_analysis.append({
                'name': feature['name'],
                'relevance': feature['relevance_score'],
                'description': feature['description'][:200] + "..."
            })
        
        # Process screenshots
        screenshot_analysis = []
        for screenshot in content['screenshots']:
            screenshot_analysis.append({
                'path': screenshot['path'],
                'relevance': screenshot['relevance_score'],
                'caption': screenshot['caption']
            })
        
        return {
            'theme': theme_query,
            'features': feature_analysis,
            'screenshots': screenshot_analysis,
            'total_matches': len(feature_analysis) + len(screenshot_analysis)
        }
    
    def find_similar_game_mechanics(self, mechanic_description: str):
        """Find games with similar mechanics"""
        features = self.search_interface.search_game_features(
            query=mechanic_description, 
            limit=15
        )
        
        # Group by game
        games_with_mechanic = {}
        for feature in features:
            game_id = feature['game_id']
            if game_id not in games_with_mechanic:
                games_with_mechanic[game_id] = []
            games_with_mechanic[game_id].append(feature)
        
        return games_with_mechanic
    
    def analyze_ui_patterns(self, ui_query: str):
        """Analyze UI patterns across games"""
        screenshots = self.search_interface.search_game_screenshots(
            query=ui_query, 
            limit=20
        )
        
        ui_patterns = []
        for screenshot in screenshots:
            ui_patterns.append({
                'game_id': screenshot['game_id'],
                'ui_description': screenshot['caption'],
                'relevance': screenshot['relevance_score'],
                'screenshot_path': screenshot['path']
            })
        
        return ui_patterns
```

### Phase 6: Setup and Initialization

#### Step 10: Create Setup Script
```python
# setup/initialize_vector_database.py
import os
import sys
from pathlib import Path

# Add project modules to path
sys.path.append(str(Path(__file__).parent.parent))

from embeddings.feature_embeddings_generator import FeatureEmbeddingsGenerator
from embeddings.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator
from vector_db.chromadb_manager import ChromaDBManager

def setup_complete_vector_database(limit_features=None, limit_screenshots=None):
    """Complete setup of vector database system"""
    
    print("=== Vector Database Setup ===")
    
    # Step 1: Generate feature embeddings
    print("\n1. Generating feature embeddings...")
    feature_generator = FeatureEmbeddingsGenerator()
    feature_embeddings = feature_generator.generate_all_feature_embeddings(
        limit=limit_features
    )
    feature_generator.save_embeddings_to_file(
        feature_embeddings, 
        "feature_embeddings.json"
    )
    print(f"✓ Generated {feature_embeddings['metadata']['total_features']} feature embeddings")
    
    # Step 2: Generate screenshot embeddings
    print("\n2. Generating screenshot embeddings...")
    screenshot_generator = ScreenshotEmbeddingsGenerator()
    screenshot_embeddings = screenshot_generator.generate_all_screenshot_embeddings(
        limit=limit_screenshots
    )
    screenshot_generator.save_embeddings_to_file(
        screenshot_embeddings, 
        "screenshot_embeddings.json"
    )
    print(f"✓ Generated {screenshot_embeddings['metadata']['total_screenshots']} screenshot embeddings")
    
    # Step 3: Initialize ChromaDB
    print("\n3. Setting up ChromaDB...")
    chroma_manager = ChromaDBManager(use_openai_embeddings=True)
    chroma_manager.create_collections()
    print("✓ ChromaDB collections created")
    
    # Step 4: Load embeddings into ChromaDB
    print("\n4. Loading embeddings into vector database...")
    feature_count = chroma_manager.load_feature_embeddings_from_json("feature_embeddings.json")
    screenshot_count = chroma_manager.load_screenshot_embeddings_from_json("screenshot_embeddings.json")
    print(f"✓ Loaded {feature_count} features and {screenshot_count} screenshots")
    
    # Step 5: Verify setup
    print("\n5. Verifying setup...")
    db_info = chroma_manager.get_database_info()
    print(f"✓ Database path: {db_info['database_path']}")
    for collection in db_info['collections']:
        print(f"✓ {collection['name']}: {collection['count']} items")
    
    print("\n=== Setup Complete ===")
    return chroma_manager

if __name__ == "__main__":
    # Setup with limited data for testing
    setup_complete_vector_database(limit_features=100, limit_screenshots=50)
```

#### Step 11: Create Test Script
```python
# tests/test_vector_search.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent_integration.vector_search_interface import GameDataSearchInterface

def test_vector_search():
    """Test the complete vector search system"""
    
    print("=== Testing Vector Search System ===")
    
    # Initialize search interface
    search_interface = GameDataSearchInterface()
    
    # Test feature search
    print("\n1. Testing feature search...")
    feature_results = search_interface.search_game_features(
        query="farming agriculture crops", 
        limit=3
    )
    
    print(f"Found {len(feature_results)} features:")
    for i, feature in enumerate(feature_results, 1):
        print(f"{i}. {feature['name']} (Score: {feature['relevance_score']:.3f})")
        print(f"   {feature['description'][:100]}...")
    
    # Test screenshot search
    print("\n2. Testing screenshot search...")
    screenshot_results = search_interface.search_game_screenshots(
        query="menu interface buttons", 
        limit=3
    )
    
    print(f"Found {len(screenshot_results)} screenshots:")
    for i, screenshot in enumerate(screenshot_results, 1):
        print(f"{i}. {screenshot['path']} (Score: {screenshot['relevance_score']:.3f})")
        print(f"   {screenshot['caption']}")
    
    # Test combined search
    print("\n3. Testing combined search...")
    all_results = search_interface.search_all_game_content(
        query="combat battle fighting", 
        limit=6
    )
    
    print(f"Found {len(all_results['features'])} features and {len(all_results['screenshots'])} screenshots")
    
    print("\n✓ All tests completed successfully!")

if __name__ == "__main__":
    test_vector_search()
```

## Usage Instructions

### For Initial Setup:
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure environment**: Update `.env.local` with database and OpenAI credentials
3. **Run complete setup**: `python setup/initialize_vector_database.py`
4. **Test system**: `python tests/test_vector_search.py`

### For Agent Integration:
```python
from agent_integration.vector_search_interface import GameDataSearchInterface

# Initialize search interface
search = GameDataSearchInterface()

# Search for relevant content
features = search.search_game_features("multiplayer cooperative gameplay")
screenshots = search.search_game_screenshots("inventory management UI")
combined = search.search_all_game_content("puzzle solving mechanics")

# Use results in your agent logic
for feature in features:
    print(f"Feature: {feature['name']} (Relevance: {feature['relevance_score']})")
```

### For Ongoing Updates:
1. **Generate new embeddings**: Run embedding generation scripts when new data is added
2. **Update vector database**: Load new embeddings into ChromaDB
3. **Monitor performance**: Check search relevance and adjust queries as needed

## File Structure Created:
```
your_project/
├── embeddings/
│   ├── feature_embeddings_generator.py
│   └── screenshot_embeddings_generator.py
├── vector_db/
│   └── chromadb_manager.py
├── agent_integration/
│   ├── vector_search_interface.py
│   └── example_agent_usage.py
├── scripts/
│   ├── generate_feature_embeddings.py
│   └── generate_screenshot_embeddings.py
├── setup/
│   └── initialize_vector_database.py
├── tests/
│   └── test_vector_search.py
├── utils/
│   └── database_connection.py
├── chroma_db/          # Created automatically
├── feature_embeddings.json
├── screenshot_embeddings.json
└── .env.local
```

## Important Notes:
- **Embedding Consistency**: Always use `text-embedding-3-large` for consistency
- **Batch Processing**: Process embeddings in batches to manage API costs
- **Error Handling**: Include proper error handling for API failures
- **Memory Management**: Consider memory usage with large datasets
- **Cost Monitoring**: Monitor OpenAI API usage and costs
- **Backup Strategy**: Implement backup for generated embeddings and ChromaDB data 