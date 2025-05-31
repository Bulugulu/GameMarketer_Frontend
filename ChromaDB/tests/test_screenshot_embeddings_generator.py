import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ChromaDB.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator

class TestScreenshotEmbeddingsGenerator(unittest.TestCase):
    """Test cases for ScreenshotEmbeddingsGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db_connection = MagicMock()
        self.mock_openai_client = MagicMock()
        
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_init(self, mock_getenv, mock_openai, mock_db_connection):
        """Test initialization of ScreenshotEmbeddingsGenerator"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        mock_openai.return_value = self.mock_openai_client
        
        generator = ScreenshotEmbeddingsGenerator()
        
        mock_db_connection.assert_called_once()
        mock_openai.assert_called_once_with(api_key='test_api_key')
        self.assertEqual(generator.db, self.mock_db_connection)
        self.assertEqual(generator.client, self.mock_openai_client)
    
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_query_screenshots_from_database(self, mock_getenv, mock_openai, mock_db_connection):
        """Test querying screenshots from database"""
        # Setup mocks
        mock_getenv.return_value = 'test_api_key'
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value = self.mock_db_connection
        self.mock_db_connection.get_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock database results with datetime
        test_datetime = datetime.now()
        mock_cursor.fetchall.return_value = [
            ('screenshot-1', '/path/to/screenshot1.png', 'game-id-1', 'Caption 1', {'elements': 'data'}, test_datetime),
            ('screenshot-2', '/path/to/screenshot2.png', 'game-id-2', 'Caption 2', None, test_datetime),
        ]
        
        generator = ScreenshotEmbeddingsGenerator()
        screenshots = generator.query_screenshots_from_database(limit=10)
        
        # Verify database query
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        
        # Verify results
        self.assertEqual(len(screenshots), 2)
        self.assertEqual(screenshots[0]['screenshot_id'], 'screenshot-1')
        self.assertEqual(screenshots[0]['path'], '/path/to/screenshot1.png')
        self.assertEqual(screenshots[0]['caption'], 'Caption 1')
        self.assertEqual(screenshots[0]['elements'], {'elements': 'data'})
    
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_format_elements_to_text_list(self, mock_getenv, mock_openai, mock_db_connection):
        """Test formatting elements list to text"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = ScreenshotEmbeddingsGenerator()
        
        # Test with list of elements
        elements = [
            {'name': 'Button1', 'type': 'button', 'description': 'Main action button'},
            {'name': 'Label1', 'type': 'label', 'description': 'Title label'}
        ]
        
        result = generator.format_elements_to_text(elements)
        expected = "Element: Button1 - Type: button - Description: Main action button; Element: Label1 - Type: label - Description: Title label"
        self.assertEqual(result, expected)
    
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_format_elements_to_text_dict(self, mock_getenv, mock_openai, mock_db_connection):
        """Test formatting single element dict to text"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = ScreenshotEmbeddingsGenerator()
        
        # Test with single element dict
        element = {'name': 'Button1', 'type': 'button', 'description': 'Main action button'}
        
        result = generator.format_elements_to_text(element)
        expected = "Element: Button1 - Type: button - Description: Main action button"
        self.assertEqual(result, expected)
    
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_format_elements_to_text_empty(self, mock_getenv, mock_openai, mock_db_connection):
        """Test formatting empty elements"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = ScreenshotEmbeddingsGenerator()
        
        # Test with None
        result = generator.format_elements_to_text(None)
        self.assertEqual(result, "")
        
        # Test with empty dict
        result = generator.format_elements_to_text({})
        self.assertEqual(result, "")
        
        # Test with empty list
        result = generator.format_elements_to_text([])
        self.assertEqual(result, "")
    
    @patch('ChromaDB.screenshot_embeddings_generator.DatabaseConnection')
    @patch('ChromaDB.screenshot_embeddings_generator.OpenAI')
    @patch('ChromaDB.screenshot_embeddings_generator.os.getenv')
    def test_combine_screenshot_text(self, mock_getenv, mock_openai, mock_db_connection):
        """Test combining screenshot caption and elements"""
        mock_getenv.return_value = 'test_api_key'
        mock_db_connection.return_value = self.mock_db_connection
        
        generator = ScreenshotEmbeddingsGenerator()
        
        # Test with both caption and elements
        screenshot = {
            'caption': 'Game menu screen',
            'elements': [{'name': 'PlayButton', 'type': 'button'}]
        }
        
        result = generator.combine_screenshot_text(screenshot)
        self.assertIn('Caption: Game menu screen', result)
        self.assertIn('UI Elements:', result)
        self.assertIn('PlayButton', result)
        
        # Test with only caption
        screenshot = {'caption': 'Game menu screen', 'elements': None}
        result = generator.combine_screenshot_text(screenshot)
        self.assertEqual(result, 'Caption: Game menu screen')
        
        # Test with only elements
        screenshot = {
            'caption': '',
            'elements': [{'name': 'PlayButton', 'type': 'button'}]
        }
        result = generator.combine_screenshot_text(screenshot)
        self.assertIn('UI Elements:', result)
        self.assertIn('PlayButton', result)
        
        # Test with neither
        screenshot = {'caption': '', 'elements': None}
        result = generator.combine_screenshot_text(screenshot)
        self.assertEqual(result, '')

if __name__ == '__main__':
    unittest.main() 