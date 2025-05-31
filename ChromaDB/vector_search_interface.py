from .chromadb_manager import ChromaDBManager
from typing import List, Dict, Any, Optional

class GameDataSearchInterface:
    """Interface for agent applications to search game data"""
    
    def __init__(self, chroma_db_path="./ChromaDB/chroma_db"):
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
            List of matching features with metadata, sorted by distance (ascending)
        """
        results = self.vector_db.search_features(query, limit, game_id)
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            formatted_results.append({
                'type': 'feature',
                'feature_id': metadata.get('feature_id', ''),  # SQL feature ID for correlation
                'name': metadata.get('name', ''),
                'description': metadata.get('description', ''),
                'game_id': metadata.get('game_id', ''),
                'distance': result['distance'],  # Show actual distance (lower = more similar)
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
            List of matching screenshots with metadata, sorted by distance (ascending)
        """
        results = self.vector_db.search_screenshots(query, limit, game_id)
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            formatted_results.append({
                'type': 'screenshot',
                'screenshot_id': metadata.get('screenshot_id', ''),  # SQL screenshot ID for correlation
                'path': metadata.get('path', ''),
                'caption': metadata.get('caption', ''),
                'game_id': metadata.get('game_id', ''),
                'distance': result['distance'],  # Show actual distance (lower = more similar)
                'content': result['document']
            })
        
        return formatted_results
    
    def search_all_game_content(self, query: str, limit: int = 10, 
                              game_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both features and screenshots
        
        Returns:
            Dictionary with 'features' and 'screenshots' keys, both sorted by distance
        """
        features = self.search_game_features(query, limit//2, game_id)
        screenshots = self.search_game_screenshots(query, limit//2, game_id)
        
        # Sort both lists by distance (ascending - lower distance = more similar)
        features.sort(key=lambda x: x['distance'])
        screenshots.sort(key=lambda x: x['distance'])
        
        return {
            'features': features,
            'screenshots': screenshots
        }
    
    def get_database_stats(self):
        """Get database statistics"""
        return self.vector_db.get_database_info() 