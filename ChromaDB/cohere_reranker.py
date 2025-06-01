import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import cohere


class CohereReranker:
    """
    Cohere reranking functionality for vector search results
    """
    
    def __init__(self):
        # Load environment variables
        load_dotenv('.env.local')
        api_key = os.getenv("COHERE_API_KEY")
        
        if not api_key:
            raise ValueError("COHERE_API_KEY not found in environment variables. Please add it to .env.local")
        
        self.client = cohere.ClientV2(api_key=api_key)
        
    def rerank_results(self, query: str, documents: List[str], 
                      top_n: Optional[int] = None,
                      model: str = "rerank-v3.5") -> List[Dict[str, Any]]:
        """
        Rerank a list of documents using Cohere's rerank model
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            top_n: Maximum number of results to return (if None, returns all)
            model: Cohere rerank model to use
            
        Returns:
            List of reranking results with relevance scores and indices
        """
        if not documents:
            return []
            
        try:
            response = self.client.rerank(
                model=model,
                query=query,
                documents=documents,
                top_n=top_n
            )
            
            # Convert response objects to dictionaries for compatibility
            rerank_results = []
            for result in response.results:
                rerank_results.append({
                    'index': result.index,
                    'relevance_score': result.relevance_score
                })
            
            return rerank_results
            
        except Exception as e:
            print(f"Error in Cohere reranking: {e}")
            # Fallback: return original order with dummy scores
            fallback_results = []
            for i, doc in enumerate(documents):
                fallback_results.append({
                    'index': i,
                    'relevance_score': 0.5  # Neutral score for fallback
                })
            return fallback_results[:top_n] if top_n else fallback_results
    
    def rerank_search_results(self, query: str, search_results: List[Dict[str, Any]], 
                             top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rerank search results from vector database
        
        Args:
            query: The original search query
            search_results: List of search results from vector database
            top_n: Maximum number of results to return
            
        Returns:
            Reranked results with relevance scores replacing distance scores
        """
        if not search_results:
            return []
        
        # Extract documents (content) for reranking
        documents = [result.get('document', '') for result in search_results]
        
        # Get reranking results
        rerank_results = self.rerank_results(query, documents, top_n)
        
        # Map back to original search results with new scores
        reranked_search_results = []
        for rerank_result in rerank_results:
            original_index = rerank_result['index']
            original_result = search_results[original_index].copy()
            
            # Replace distance with relevance_score
            original_result['relevance_score'] = rerank_result['relevance_score']
            # Keep original distance for debugging if needed
            original_result['original_distance'] = original_result.get('distance', 0.0)
            # Remove distance field to avoid confusion
            if 'distance' in original_result:
                del original_result['distance']
                
            reranked_search_results.append(original_result)
        
        return reranked_search_results 