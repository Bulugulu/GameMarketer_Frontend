"""
Pytest configuration file for ChromaDB tests

This file contains common fixtures and configuration for pytest-based testing.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@pytest.fixture
def mock_database_connection():
    """Mock DatabaseConnection for testing"""
    with patch('ChromaDB.database_connection.pg8000.dbapi.connect'):
        with patch('ChromaDB.database_connection.load_dotenv'):
            with patch('ChromaDB.database_connection.os.getenv') as mock_getenv:
                mock_getenv.side_effect = lambda key, default=None: {
                    'PG_USER': 'test_user',
                    'PG_PASSWORD': 'test_password',
                    'PG_HOST': 'localhost',
                    'PG_PORT': '5432',
                    'PG_DATABASE': 'test_db'
                }.get(key, default)
                
                from ChromaDB.database_connection import DatabaseConnection
                yield DatabaseConnection()

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = MagicMock()
    
    # Mock embedding response
    mock_response = MagicMock()
    mock_response.data[0].embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    mock_response.usage.total_tokens = 10
    mock_client.embeddings.create.return_value = mock_response
    
    return mock_client

@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client for testing"""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    
    # Mock collection operations
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_client.get_collection.return_value = mock_collection
    
    # Mock search results
    mock_collection.query.return_value = {
        'ids': [['id1', 'id2']],
        'documents': [['doc1', 'doc2']],
        'metadatas': [[{'name': 'Test1'}, {'name': 'Test2'}]],
        'distances': [[0.1, 0.2]]
    }
    
    mock_collection.count.return_value = 10
    
    return mock_client

@pytest.fixture
def sample_feature_data():
    """Sample feature data for testing"""
    return [
        {
            'feature_id': 1,
            'name': 'Test Feature 1',
            'description': 'Description for test feature 1',
            'game_id': 'game-1'
        },
        {
            'feature_id': 2,
            'name': 'Test Feature 2',
            'description': 'Description for test feature 2',
            'game_id': 'game-2'
        }
    ]

@pytest.fixture
def sample_screenshot_data():
    """Sample screenshot data for testing"""
    from datetime import datetime
    
    return [
        {
            'screenshot_id': 'screenshot-1',
            'path': '/path/to/screenshot1.png',
            'game_id': 'game-1',
            'caption': 'Test caption 1',
            'elements': [{'name': 'Button1', 'type': 'button'}],
            'capture_time': datetime.now().isoformat()
        },
        {
            'screenshot_id': 'screenshot-2',
            'path': '/path/to/screenshot2.png',
            'game_id': 'game-2',
            'caption': 'Test caption 2',
            'elements': None,
            'capture_time': datetime.now().isoformat()
        }
    ]

@pytest.fixture
def sample_embeddings_data():
    """Sample embeddings data for testing"""
    return {
        'metadata': {
            'total_features': 2,
            'model': 'text-embedding-3-large',
            'generated_at': '2023-01-01T00:00:00',
            'total_tokens': 20
        },
        'features': [
            {
                'feature_id': 1,
                'name': 'Test Feature',
                'description': 'Test Description',
                'game_id': 'game-1',
                'combined_text': 'Test Feature - Test Description',
                'embedding': [0.1, 0.2, 0.3],
                'success': True,
                'model': 'text-embedding-3-large',
                'actual_tokens': 10
            }
        ]
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    ) 