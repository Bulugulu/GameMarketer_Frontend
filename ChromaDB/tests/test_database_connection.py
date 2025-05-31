import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ChromaDB.database_connection import DatabaseConnection

class TestDatabaseConnection(unittest.TestCase):
    """Test cases for DatabaseConnection class"""
    
    @patch('ChromaDB.database_connection.load_dotenv')
    @patch('ChromaDB.database_connection.pg8000.dbapi.connect')
    @patch('ChromaDB.database_connection.os.getenv')
    def test_init_successful_connection(self, mock_getenv, mock_connect, mock_load_dotenv):
        """Test successful database connection initialization"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_password',
            'PG_HOST': 'localhost',
            'PG_PORT': '5432',
            'PG_DATABASE': 'test_db'
        }.get(key, default)
        
        # Mock successful connection
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        # Test initialization
        db = DatabaseConnection()
        
        # Verify calls
        mock_load_dotenv.assert_called_once_with('.env.local')
        mock_connect.assert_called_once_with(
            user='test_user',
            password='test_password',
            host='localhost',
            port=5432,
            database='test_db'
        )
        
        # Verify connection is stored
        self.assertEqual(db.conn, mock_connection)
    
    @patch('ChromaDB.database_connection.load_dotenv')
    @patch('ChromaDB.database_connection.pg8000.dbapi.connect')
    @patch('ChromaDB.database_connection.os.getenv')
    def test_get_connection(self, mock_getenv, mock_connect, mock_load_dotenv):
        """Test get_connection method returns the connection"""
        mock_getenv.side_effect = lambda key, default=None: {
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_password',
            'PG_HOST': 'localhost',
            'PG_PORT': '5432',
            'PG_DATABASE': 'test_db'
        }.get(key, default)
        
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        db = DatabaseConnection()
        connection = db.get_connection()
        
        self.assertEqual(connection, mock_connection)
    
    @patch('ChromaDB.database_connection.load_dotenv')
    @patch('ChromaDB.database_connection.pg8000.dbapi.connect')
    @patch('ChromaDB.database_connection.os.getenv')
    def test_close_connection(self, mock_getenv, mock_connect, mock_load_dotenv):
        """Test close method closes the connection"""
        mock_getenv.side_effect = lambda key, default=None: {
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_password',
            'PG_HOST': 'localhost',
            'PG_PORT': '5432',
            'PG_DATABASE': 'test_db'
        }.get(key, default)
        
        mock_connection = MagicMock()
        mock_connect.return_value = mock_connection
        
        db = DatabaseConnection()
        db.close()
        
        mock_connection.close.assert_called_once()
    
    @patch('ChromaDB.database_connection.load_dotenv')
    @patch('ChromaDB.database_connection.pg8000.dbapi.connect')
    @patch('ChromaDB.database_connection.os.getenv')
    def test_close_with_no_connection(self, mock_getenv, mock_connect, mock_load_dotenv):
        """Test close method handles None connection gracefully"""
        mock_getenv.side_effect = lambda key, default=None: {
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_password',
            'PG_HOST': 'localhost',
            'PG_PORT': '5432',
            'PG_DATABASE': 'test_db'
        }.get(key, default)
        
        mock_connect.return_value = None
        
        db = DatabaseConnection()
        db.conn = None
        
        # Should not raise an exception
        db.close()

if __name__ == '__main__':
    unittest.main() 