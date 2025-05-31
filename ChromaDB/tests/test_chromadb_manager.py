import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ChromaDB.chromadb_manager import ChromaDBManager

class TestChromaDBManager(unittest.TestCase):
    """Test cases for ChromaDBManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_client = MagicMock()
        self.mock_collection = MagicMock()
        
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    @patch('ChromaDB.chromadb_manager.load_dotenv')
    @patch('ChromaDB.chromadb_manager.os.getenv')
    @patch('ChromaDB.chromadb_manager.embedding_functions.OpenAIEmbeddingFunction')
    def test_init_with_openai_embeddings(self, mock_embedding_func, mock_getenv, mock_load_dotenv, mock_persistent_client):
        """Test initialization with OpenAI embeddings"""
        # Setup mocks
        mock_getenv.return_value = 'test_api_key'
        mock_persistent_client.return_value = self.mock_client
        mock_embedding_function = MagicMock()
        mock_embedding_func.return_value = mock_embedding_function
        
        # Test initialization
        manager = ChromaDBManager(use_openai_embeddings=True)
        
        # Verify calls
        mock_load_dotenv.assert_called_once_with('.env.local')
        mock_getenv.assert_called_once_with("OPENAI_API_KEY")
        mock_embedding_func.assert_called_once_with(
            api_key='test_api_key',
            model_name="text-embedding-3-large"
        )
        
        # Verify properties
        self.assertEqual(manager.client, self.mock_client)
        self.assertEqual(manager.embedding_function, mock_embedding_function)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_init_without_openai_embeddings(self, mock_persistent_client):
        """Test initialization without OpenAI embeddings"""
        mock_persistent_client.return_value = self.mock_client
        
        manager = ChromaDBManager(use_openai_embeddings=False)
        
        self.assertEqual(manager.client, self.mock_client)
        self.assertIsNone(manager.embedding_function)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    @patch('ChromaDB.chromadb_manager.datetime')
    def test_create_collections(self, mock_datetime, mock_persistent_client):
        """Test creating ChromaDB collections"""
        # Setup mocks
        mock_persistent_client.return_value = self.mock_client
        mock_datetime.now.return_value.isoformat.return_value = '2023-01-01T00:00:00'
        
        mock_features_collection = MagicMock()
        mock_screenshots_collection = MagicMock()
        
        self.mock_client.get_or_create_collection.side_effect = [
            mock_features_collection,
            mock_screenshots_collection
        ]
        
        manager = ChromaDBManager(use_openai_embeddings=False)
        features_coll, screenshots_coll = manager.create_collections()
        
        # Verify collection creation calls
        self.assertEqual(self.mock_client.get_or_create_collection.call_count, 2)
        
        # Verify returned collections
        self.assertEqual(features_coll, mock_features_collection)
        self.assertEqual(screenshots_coll, mock_screenshots_collection)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_load_feature_embeddings_from_json(self, mock_persistent_client):
        """Test loading feature embeddings from JSON file"""
        mock_persistent_client.return_value = self.mock_client
        self.mock_client.get_or_create_collection.return_value = self.mock_collection
        
        # Mock JSON data
        test_data = '{"features": [{"feature_id": 1, "name": "Test", "embedding": [0.1, 0.2], "success": true}], "metadata": {"generated_at": "2023-01-01"}}'
        
        with patch('builtins.open', mock_open(read_data=test_data)):
            manager = ChromaDBManager(use_openai_embeddings=False)
            count = manager.load_feature_embeddings_from_json('test.json')
        
        # Verify collection was called
        self.mock_client.get_or_create_collection.assert_called_with(
            name="game_features",
            embedding_function=None
        )
        
        # Verify data was added to collection
        self.mock_collection.add.assert_called()
        self.assertEqual(count, 1)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_load_screenshot_embeddings_from_json(self, mock_persistent_client):
        """Test loading screenshot embeddings from JSON file"""
        mock_persistent_client.return_value = self.mock_client
        self.mock_client.get_or_create_collection.return_value = self.mock_collection
        
        # Mock JSON data
        test_data = '{"screenshots": [{"screenshot_id": "1", "path": "/test.png", "embedding": [0.1, 0.2], "success": true}], "metadata": {"generated_at": "2023-01-01"}}'
        
        with patch('builtins.open', mock_open(read_data=test_data)):
            manager = ChromaDBManager(use_openai_embeddings=False)
            count = manager.load_screenshot_embeddings_from_json('test.json')
        
        # Verify collection was called
        self.mock_client.get_or_create_collection.assert_called_with(
            name="game_screenshots",
            embedding_function=None
        )
        
        # Verify data was added to collection
        self.mock_collection.add.assert_called()
        self.assertEqual(count, 1)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_search_features(self, mock_persistent_client):
        """Test searching features"""
        mock_persistent_client.return_value = self.mock_client
        self.mock_client.get_collection.return_value = self.mock_collection
        
        # Mock search results
        mock_results = {
            'ids': [['feature_1', 'feature_2']],
            'documents': [['doc1', 'doc2']],
            'metadatas': [[{'name': 'Feature 1'}, {'name': 'Feature 2'}]],
            'distances': [[0.1, 0.2]]
        }
        self.mock_collection.query.return_value = mock_results
        
        manager = ChromaDBManager(use_openai_embeddings=False)
        results = manager.search_features("test query", n_results=5)
        
        # Verify search call
        self.mock_collection.query.assert_called_once_with(
            query_texts=["test query"],
            n_results=5,
            where=None
        )
        
        # Verify results format
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 'feature_1')
        self.assertEqual(results[0]['document'], 'doc1')
        self.assertEqual(results[0]['distance'], 0.1)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_search_features_with_game_id_filter(self, mock_persistent_client):
        """Test searching features with game ID filter"""
        mock_persistent_client.return_value = self.mock_client
        self.mock_client.get_collection.return_value = self.mock_collection
        
        mock_results = {
            'ids': [['feature_1']],
            'documents': [['doc1']],
            'metadatas': [[{'name': 'Feature 1'}]],
            'distances': [[0.1]]
        }
        self.mock_collection.query.return_value = mock_results
        
        manager = ChromaDBManager(use_openai_embeddings=False)
        results = manager.search_features("test query", n_results=5, game_id="test-game")
        
        # Verify search call with where clause
        self.mock_collection.query.assert_called_once_with(
            query_texts=["test query"],
            n_results=5,
            where={"game_id": "test-game"}
        )
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_get_database_info(self, mock_persistent_client):
        """Test getting database information"""
        mock_persistent_client.return_value = self.mock_client
        
        # Mock collections
        mock_features_collection = MagicMock()
        mock_features_collection.count.return_value = 10
        mock_screenshots_collection = MagicMock()
        mock_screenshots_collection.count.return_value = 20
        
        self.mock_client.get_collection.side_effect = [
            mock_features_collection,
            mock_screenshots_collection
        ]
        
        manager = ChromaDBManager(db_path="./test_path", use_openai_embeddings=False)
        info = manager.get_database_info()
        
        # Verify info structure
        self.assertIn('database_path', info)
        self.assertIn('collections', info)
        self.assertEqual(len(info['collections']), 2)
        self.assertEqual(info['collections'][0]['name'], 'game_features')
        self.assertEqual(info['collections'][0]['count'], 10)
        self.assertEqual(info['collections'][1]['name'], 'game_screenshots')
        self.assertEqual(info['collections'][1]['count'], 20)
    
    @patch('ChromaDB.chromadb_manager.chromadb.PersistentClient')
    def test_get_database_info_with_missing_collections(self, mock_persistent_client):
        """Test getting database info when collections don't exist"""
        mock_persistent_client.return_value = self.mock_client
        
        # Mock exception for missing collections
        self.mock_client.get_collection.side_effect = Exception("Collection not found")
        
        manager = ChromaDBManager(use_openai_embeddings=False)
        info = manager.get_database_info()
        
        # Verify graceful handling of missing collections
        self.assertEqual(info['collections'][0]['count'], 0)
        self.assertEqual(info['collections'][1]['count'], 0)

if __name__ == '__main__':
    unittest.main() 