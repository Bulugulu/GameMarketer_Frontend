import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ChromaDB.feature_embeddings_generator import FeatureEmbeddingsGenerator

class TestFeatureEmbeddingsGenerator(unittest.TestCase):
    """Test cases for FeatureEmbeddingsGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_connection = MagicMock()
        self.mock_openai_client = MagicMock()
        
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_init(self, mock_getenv, mock_openai, mock_db_connection):
        """Test initialization of FeatureEmbeddingsGenerator"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        mock_openai.return_value = self.mock_openai_client
        
        generator = FeatureEmbeddingsGenerator()
        
        mock_db_connection.assert_called_once()
        mock_openai.assert_called_once_with(api_key='test_api_key')
        self.assertEqual(generator.db, self.mock_db_connection)
        self.assertEqual(generator.client, self.mock_openai_client)
    
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_query_features_from_database(self, mock_getenv, mock_openai, mock_db_connection):
        """Test querying features from database"""
        # Setup mocks
        mock_getenv.return_value = 'test_api_key'
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value = self.mock_db_connection
        self.mock_db_connection.get_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock database results
        mock_cursor.fetchall.return_value = [
            (1, 'Feature 1', 'Description 1', 'game-id-1'),
            (2, 'Feature 2', 'Description 2', 'game-id-2'),
        ]
        
        generator = FeatureEmbeddingsGenerator()
        features = generator.query_features_from_database(limit=10)
        
        # Verify database query
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        
        # Verify results
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0]['feature_id'], 1)
        self.assertEqual(features[0]['name'], 'Feature 1')
        self.assertEqual(features[0]['description'], 'Description 1')
        self.assertEqual(features[0]['game_id'], 'game-id-1')
    
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_combine_feature_text(self, mock_getenv, mock_openai, mock_db_connection):
        """Test combining feature name and description"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = FeatureEmbeddingsGenerator()
        
        # Test with both name and description
        feature = {'name': 'Test Feature', 'description': 'Test Description'}
        result = generator.combine_feature_text(feature)
        self.assertEqual(result, 'Test Feature - Test Description')
        
        # Test with only name
        feature = {'name': 'Test Feature', 'description': ''}
        result = generator.combine_feature_text(feature)
        self.assertEqual(result, 'Test Feature')
        
        # Test with only description
        feature = {'name': '', 'description': 'Test Description'}
        result = generator.combine_feature_text(feature)
        self.assertEqual(result, 'Test Description')
        
        # Test with neither
        feature = {'name': '', 'description': ''}
        result = generator.combine_feature_text(feature)
        self.assertEqual(result, '')
    
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_generate_embedding_for_text_success(self, mock_getenv, mock_openai, mock_db_connection):
        """Test successful embedding generation"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_response.usage.total_tokens = 10
        self.mock_openai_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = self.mock_openai_client
        
        generator = FeatureEmbeddingsGenerator()
        result = generator.generate_embedding_for_text("test text")
        
        # Verify OpenAI call
        self.mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="test text",
            encoding_format="float"
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['embedding'], [0.1, 0.2, 0.3])
        self.assertEqual(result['tokens'], 10)
        self.assertEqual(result['model'], 'text-embedding-3-large')
    
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_generate_embedding_for_text_failure(self, mock_getenv, mock_openai, mock_db_connection):
        """Test embedding generation failure"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        # Mock OpenAI exception
        self.mock_openai_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = self.mock_openai_client
        
        generator = FeatureEmbeddingsGenerator()
        result = generator.generate_embedding_for_text("test text")
        
        # Verify result
        self.assertFalse(result['success'])
        self.assertEqual(result['embedding'], [])
        self.assertEqual(result['error'], "API Error")
    
    @patch('ChromaDB.feature_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.feature_embeddings_generator.OpenAI')
    @patch('ChromaDB.feature_embeddings_generator.os.getenv')
    def test_save_embeddings_to_file(self, mock_getenv, mock_openai, mock_db_connection):
        """Test saving embeddings to file"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = FeatureEmbeddingsGenerator()
        
        test_data = {'test': 'data'}
        mock_file = mock_open()
        
        with patch('builtins.open', mock_file):
            generator.save_embeddings_to_file(test_data, 'test.json')
        
        # Verify file operations
        mock_file.assert_called_once_with('test.json', 'w', encoding='utf-8')
        handle = mock_file()
        # Verify json.dump was called (indirectly through the file write)
        self.assertTrue(handle.write.called)

if __name__ == '__main__':
    unittest.main() 