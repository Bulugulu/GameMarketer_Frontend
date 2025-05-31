import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ChromaDB.vector_search_interface import GameDataSearchInterface

class TestGameDataSearchInterface(unittest.TestCase):
    """Test cases for GameDataSearchInterface class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_vector_db = MagicMock()
        
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_init(self, mock_chromadb_manager):
        """Test initialization of GameDataSearchInterface"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        interface = GameDataSearchInterface(chroma_db_path="./test_path")
        
        mock_chromadb_manager.assert_called_once_with(
            db_path="./test_path",
            use_openai_embeddings=True
        )
        self.assertEqual(interface.vector_db, self.mock_vector_db)
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_search_game_features(self, mock_chromadb_manager):
        """Test searching game features"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        # Mock ChromaDB results
        mock_chromadb_results = [
            {
                'id': 'feature_1',
                'document': 'Feature description',
                'metadata': {
                    'name': 'Test Feature',
                    'description': 'Test description',
                    'game_id': 'game-1'
                },
                'distance': 0.2
            },
            {
                'id': 'feature_2',
                'document': 'Another feature',
                'metadata': {
                    'name': 'Another Feature',
                    'description': 'Another description',
                    'game_id': 'game-2'
                },
                'distance': 0.3
            }
        ]
        self.mock_vector_db.search_features.return_value = mock_chromadb_results
        
        interface = GameDataSearchInterface()
        results = interface.search_game_features("test query", limit=5, game_id="game-1")
        
        # Verify ChromaDB search call
        self.mock_vector_db.search_features.assert_called_once_with("test query", 5, "game-1")
        
        # Verify results format
        self.assertEqual(len(results), 2)
        
        # Verify first result
        result1 = results[0]
        self.assertEqual(result1['type'], 'feature')
        self.assertEqual(result1['name'], 'Test Feature')
        self.assertEqual(result1['description'], 'Test description')
        self.assertEqual(result1['game_id'], 'game-1')
        self.assertEqual(result1['relevance_score'], 0.8)  # 1 - 0.2
        self.assertEqual(result1['content'], 'Feature description')
        
        # Verify second result
        result2 = results[1]
        self.assertEqual(result2['relevance_score'], 0.7)  # 1 - 0.3
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_search_game_screenshots(self, mock_chromadb_manager):
        """Test searching game screenshots"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        # Mock ChromaDB results
        mock_chromadb_results = [
            {
                'id': 'screenshot_1',
                'document': 'Screenshot description',
                'metadata': {
                    'path': '/path/to/screenshot1.png',
                    'caption': 'Menu screen',
                    'game_id': 'game-1'
                },
                'distance': 0.1
            }
        ]
        self.mock_vector_db.search_screenshots.return_value = mock_chromadb_results
        
        interface = GameDataSearchInterface()
        results = interface.search_game_screenshots("menu interface", limit=3)
        
        # Verify ChromaDB search call
        self.mock_vector_db.search_screenshots.assert_called_once_with("menu interface", 3, None)
        
        # Verify results format
        self.assertEqual(len(results), 1)
        
        result = results[0]
        self.assertEqual(result['type'], 'screenshot')
        self.assertEqual(result['path'], '/path/to/screenshot1.png')
        self.assertEqual(result['caption'], 'Menu screen')
        self.assertEqual(result['game_id'], 'game-1')
        self.assertEqual(result['relevance_score'], 0.9)  # 1 - 0.1
        self.assertEqual(result['content'], 'Screenshot description')
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_search_all_game_content(self, mock_chromadb_manager):
        """Test searching all game content (features and screenshots)"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        # Mock return values for both search methods
        mock_feature_results = [
            {
                'id': 'feature_1',
                'document': 'Feature doc',
                'metadata': {'name': 'Feature 1', 'description': 'Desc 1', 'game_id': 'game-1'},
                'distance': 0.2
            }
        ]
        
        mock_screenshot_results = [
            {
                'id': 'screenshot_1',
                'document': 'Screenshot doc',
                'metadata': {'path': '/path1.png', 'caption': 'Caption 1', 'game_id': 'game-1'},
                'distance': 0.1
            }
        ]
        
        self.mock_vector_db.search_features.return_value = mock_feature_results
        self.mock_vector_db.search_screenshots.return_value = mock_screenshot_results
        
        interface = GameDataSearchInterface()
        results = interface.search_all_game_content("test query", limit=10, game_id="game-1")
        
        # Verify both search methods were called
        self.mock_vector_db.search_features.assert_called_once_with("test query", 5, "game-1")  # limit//2
        self.mock_vector_db.search_screenshots.assert_called_once_with("test query", 5, "game-1")  # limit//2
        
        # Verify results structure
        self.assertIn('features', results)
        self.assertIn('screenshots', results)
        self.assertEqual(len(results['features']), 1)
        self.assertEqual(len(results['screenshots']), 1)
        
        # Verify feature result
        feature = results['features'][0]
        self.assertEqual(feature['type'], 'feature')
        self.assertEqual(feature['name'], 'Feature 1')
        
        # Verify screenshot result
        screenshot = results['screenshots'][0]
        self.assertEqual(screenshot['type'], 'screenshot')
        self.assertEqual(screenshot['path'], '/path1.png')
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_get_database_stats(self, mock_chromadb_manager):
        """Test getting database statistics"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        mock_db_info = {
            'database_path': '/test/path',
            'collections': [
                {'name': 'game_features', 'count': 100},
                {'name': 'game_screenshots', 'count': 200}
            ]
        }
        self.mock_vector_db.get_database_info.return_value = mock_db_info
        
        interface = GameDataSearchInterface()
        stats = interface.get_database_stats()
        
        # Verify call to underlying manager
        self.mock_vector_db.get_database_info.assert_called_once()
        
        # Verify stats are returned as-is
        self.assertEqual(stats, mock_db_info)
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_search_with_empty_results(self, mock_chromadb_manager):
        """Test search methods with empty results"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        # Mock empty results
        self.mock_vector_db.search_features.return_value = []
        self.mock_vector_db.search_screenshots.return_value = []
        
        interface = GameDataSearchInterface()
        
        # Test feature search with empty results
        feature_results = interface.search_game_features("nonexistent query")
        self.assertEqual(len(feature_results), 0)
        
        # Test screenshot search with empty results
        screenshot_results = interface.search_game_screenshots("nonexistent query")
        self.assertEqual(len(screenshot_results), 0)
        
        # Test combined search with empty results
        combined_results = interface.search_all_game_content("nonexistent query")
        self.assertEqual(len(combined_results['features']), 0)
        self.assertEqual(len(combined_results['screenshots']), 0)
    
    @patch('ChromaDB.vector_search_interface.ChromaDBManager')
    def test_search_with_missing_metadata_fields(self, mock_chromadb_manager):
        """Test search methods handle missing metadata fields gracefully"""
        mock_chromadb_manager.return_value = self.mock_vector_db
        
        # Mock results with missing metadata fields
        mock_feature_results = [
            {
                'id': 'feature_1',
                'document': 'Feature doc',
                'metadata': {},  # Empty metadata
                'distance': 0.2
            }
        ]
        
        mock_screenshot_results = [
            {
                'id': 'screenshot_1',
                'document': 'Screenshot doc',
                'metadata': {'path': '/path1.png'},  # Missing caption and game_id
                'distance': 0.1
            }
        ]
        
        self.mock_vector_db.search_features.return_value = mock_feature_results
        self.mock_vector_db.search_screenshots.return_value = mock_screenshot_results
        
        interface = GameDataSearchInterface()
        
        # Test feature search with missing metadata
        feature_results = interface.search_game_features("test query")
        self.assertEqual(len(feature_results), 1)
        self.assertEqual(feature_results[0]['name'], '')  # Should default to empty string
        self.assertEqual(feature_results[0]['description'], '')
        self.assertEqual(feature_results[0]['game_id'], '')
        
        # Test screenshot search with missing metadata
        screenshot_results = interface.search_game_screenshots("test query")
        self.assertEqual(len(screenshot_results), 1)
        self.assertEqual(screenshot_results[0]['path'], '/path1.png')
        self.assertEqual(screenshot_results[0]['caption'], '')  # Should default to empty string
        self.assertEqual(screenshot_results[0]['game_id'], '')

if __name__ == '__main__':
    unittest.main() 