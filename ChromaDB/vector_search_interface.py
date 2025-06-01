from .chromadb_manager import ChromaDBManager
from .cohere_reranker import CohereReranker
from typing import List, Dict, Any, Optional

class GameDataSearchInterface:
    """Interface for agent applications to search game data"""
    
    def __init__(self, chroma_db_path="./ChromaDB/chroma_db", use_reranking=True, rerank_top_k=50):
        self.vector_db = ChromaDBManager(
            db_path=chroma_db_path, 
            use_openai_embeddings=True
        )
        
        # Initialize reranker if enabled
        self.use_reranking = use_reranking
        self.rerank_top_k = rerank_top_k  # Get more results from vector search before reranking
        self.reranker = None
        
        if use_reranking:
            try:
                self.reranker = CohereReranker()
                print("✓ Cohere reranker initialized successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize Cohere reranker: {e}")
                print("   Falling back to vector similarity search only")
                self.use_reranking = False
        
    def search_game_features(self, query: str, limit: int = 10, 
                           game_id: Optional[str] = None,
                           feature_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for game features relevant to query
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            game_id: Optional filter by specific game
            feature_ids: Optional list of specific feature IDs to search within
            
        Returns:
            List of matching features with metadata, sorted by relevance (if reranking) or distance
        """
        # If reranking is enabled, get more initial results to improve reranking quality
        search_limit = max(self.rerank_top_k, limit * 2) if self.use_reranking else limit
        
        results = self.vector_db.search_features(query, search_limit, game_id, feature_ids)
        
        # Apply reranking if available
        if self.use_reranking and self.reranker and results:
            try:
                results = self.reranker.rerank_search_results(query, results, top_n=limit)
            except Exception as e:
                print(f"Warning: Reranking failed, using vector similarity: {e}")
                # Fall back to vector similarity results
                results = results[:limit]
        else:
            # Use original vector similarity results
            results = results[:limit]
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            
            # Create result dict with appropriate scoring field
            result_dict = {
                'type': 'feature',
                'feature_id': metadata.get('feature_id', ''),  # SQL feature ID for correlation
                'name': metadata.get('name', ''),
                'description': metadata.get('description', ''),
                'game_id': metadata.get('game_id', ''),
                'content': result['document']
            }
            
            # Add either relevance_score (reranked) or distance (vector similarity)
            if 'relevance_score' in result:
                result_dict['relevance_score'] = result['relevance_score']
                # Also include original distance for debugging
                if 'original_distance' in result:
                    result_dict['original_distance'] = result['original_distance']
            else:
                result_dict['distance'] = result['distance']  # Original distance field
            
            formatted_results.append(result_dict)
        
        return formatted_results
    
    def search_game_screenshots(self, query: str, limit: int = 10, 
                              game_id: Optional[str] = None,
                              screenshot_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for game screenshots relevant to query
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            game_id: Optional filter by specific game
            screenshot_ids: Optional list of specific screenshot IDs to search within
            
        Returns:
            List of matching screenshots with metadata, sorted by relevance (if reranking) or distance
        """
        # If reranking is enabled, get more initial results to improve reranking quality
        search_limit = max(self.rerank_top_k, limit * 2) if self.use_reranking else limit
        
        results = self.vector_db.search_screenshots(query, search_limit, game_id, screenshot_ids)
        
        # Apply reranking if available
        if self.use_reranking and self.reranker and results:
            try:
                results = self.reranker.rerank_search_results(query, results, top_n=limit)
            except Exception as e:
                print(f"Warning: Reranking failed, using vector similarity: {e}")
                # Fall back to vector similarity results
                results = results[:limit]
        else:
            # Use original vector similarity results
            results = results[:limit]
        
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            
            # Create result dict with appropriate scoring field
            result_dict = {
                'type': 'screenshot',
                'screenshot_id': metadata.get('screenshot_id', ''),  # SQL screenshot ID for correlation
                'path': metadata.get('path', ''),
                'caption': metadata.get('caption', ''),
                'game_id': metadata.get('game_id', ''),
                'content': result['document']
            }
            
            # Add either relevance_score (reranked) or distance (vector similarity)
            if 'relevance_score' in result:
                result_dict['relevance_score'] = result['relevance_score']
                # Also include original distance for debugging
                if 'original_distance' in result:
                    result_dict['original_distance'] = result['original_distance']
            else:
                result_dict['distance'] = result['distance']  # Original distance field
            
            formatted_results.append(result_dict)
        
        return formatted_results
    
    def search_all_game_content(self, query: str, limit: int = 10, 
                              game_id: Optional[str] = None,
                              feature_ids: Optional[List[str]] = None,
                              screenshot_ids: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both features and screenshots
        
        Args:
            query: Natural language search query
            limit: Maximum number of results for EACH content type (features and screenshots)
            game_id: Optional filter by specific game
            feature_ids: Optional list of specific feature IDs to search within
            screenshot_ids: Optional list of specific screenshot IDs to search within
        
        Returns:
            Dictionary with 'features' and 'screenshots' keys, both sorted by relevance/distance
        """
        # Get the specified limit for each content type (not divided)
        features = self.search_game_features(query, limit, game_id, feature_ids)
        screenshots = self.search_game_screenshots(query, limit, game_id, screenshot_ids)
        
        # Sort both lists by the appropriate scoring metric
        # If reranking is used, sort by relevance_score (descending - higher is better)
        # If no reranking, sort by distance (ascending - lower is better)
        if features and 'relevance_score' in features[0]:
            features.sort(key=lambda x: x['relevance_score'], reverse=True)
        elif features and 'distance' in features[0]:
            features.sort(key=lambda x: x['distance'])
            
        if screenshots and 'relevance_score' in screenshots[0]:
            screenshots.sort(key=lambda x: x['relevance_score'], reverse=True)
        elif screenshots and 'distance' in screenshots[0]:
            screenshots.sort(key=lambda x: x['distance'])
        
        return {
            'features': features,
            'screenshots': screenshots
        }
    
    def get_database_stats(self):
        """Get database statistics"""
        stats = self.vector_db.get_database_info()
        # Add reranking status to stats
        stats['reranking_enabled'] = self.use_reranking
        if self.use_reranking:
            stats['rerank_top_k'] = self.rerank_top_k
        return stats 