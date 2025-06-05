#!/usr/bin/env python3
"""
Test script for the ChromaDB vector search system
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.vector_search_interface import GameDataSearchInterface
from ChromaDB.chromadb_manager import ChromaDBManager

def test_vector_search():
    """Test the complete vector search system"""
    
    print("=== Testing ChromaDB Vector Search System ===")
    
    try:
        # Initialize search interface
        search_interface = GameDataSearchInterface()
        
        # Get database stats
        print("\n📊 Database Statistics:")
        stats = search_interface.get_database_stats()
        print(f"Database path: {stats['database_path']}")
        
        # Show reranking status
        if stats.get('reranking_enabled', False):
            print(f"🎯 Cohere Reranking: ✅ ENABLED (top-k: {stats.get('rerank_top_k', 50)})")
            print(f"   📈 Results will show relevance_score (higher = more relevant)")
        else:
            print(f"🎯 Cohere Reranking: ❌ DISABLED")
            print(f"   📊 Results will show distance (lower = more similar)")
        
        # Enhanced: Check embedding dimensions
        print("\n🔍 Checking Embedding Dimensions:")
        chroma_manager = ChromaDBManager()
        
        for collection_info in stats['collections']:
            collection_name = collection_info['name']
            count = collection_info['count']
            
            print(f"\n📁 Collection: {collection_name} ({count} items)")
            
            if count > 0:
                try:
                    collection = chroma_manager.client.get_collection(collection_name)
                    # Get one embedding to check dimensions
                    sample = collection.get(limit=1, include=['embeddings', 'metadatas'])
                    
                    # More robust checking to avoid numpy array boolean issues
                    embeddings_exist = False
                    dimensions = 0
                    
                    try:
                        if (sample and 
                            'embeddings' in sample and 
                            sample['embeddings'] and 
                            len(sample['embeddings']) > 0):
                            
                            first_embedding = sample['embeddings'][0]
                            if first_embedding is not None and hasattr(first_embedding, '__len__'):
                                dimensions = len(first_embedding)
                                embeddings_exist = True
                    except Exception:
                        embeddings_exist = False
                    
                    if embeddings_exist and dimensions > 0:
                        print(f"   ✅ Embedding dimensions: {dimensions}")
                        
                        # Check metadata for additional info
                        try:
                            if (sample.get('metadatas') and 
                                len(sample['metadatas']) > 0 and 
                                sample['metadatas'][0]):
                                
                                metadata = sample['metadatas'][0]
                                model = metadata.get('model', 'Unknown')
                                has_content_hash = 'content_hash' in metadata
                                
                                print(f"   📝 Model: {model}")
                                print(f"   🔄 Change detection: {'Enhanced' if has_content_hash else 'Basic'}")
                        except Exception:
                            pass  # Skip metadata if there's an issue
                    else:
                        print(f"   ⚠️  No embeddings found or invalid format")
                        
                except Exception as e:
                    print(f"   ❌ Error checking collection: {str(e)}")
            else:
                print(f"   ⚠️  Collection is empty")
        
        # Test feature search
        print("\n🔍 Testing feature search...")
        test_queries = [
            "farming agriculture crops",
            "combat battle fighting", 
            "building construction",
            "social interaction multiplayer"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            feature_results = search_interface.search_game_features(query=query, limit=3)
            
            if feature_results:
                print(f"Found {len(feature_results)} features:")
                for i, feature in enumerate(feature_results, 1):
                    # Display appropriate score based on what's available
                    if 'relevance_score' in feature:
                        score_text = f"Relevance: {feature['relevance_score']:.3f}"
                        if 'original_distance' in feature:
                            score_text += f" (was distance: {feature['original_distance']:.3f})"
                    else:
                        score_text = f"Distance: {feature['distance']:.3f}"
                    
                    print(f"  {i}. {feature['name']} ({score_text})")
                    print(f"     Game: {feature['game_id']}")
                    print(f"     Description: {feature['description'][:100]}...")
            else:
                print("  No features found")
        
        # Test screenshot search
        print("\n📸 Testing screenshot search...")
        screenshot_queries = [
            "menu interface buttons",
            "game inventory items",
            "character selection screen"
        ]
        
        for query in screenshot_queries:
            print(f"\nQuery: '{query}'")
            screenshot_results = search_interface.search_game_screenshots(query=query, limit=3)
            
            if screenshot_results:
                print(f"Found {len(screenshot_results)} screenshots:")
                for i, screenshot in enumerate(screenshot_results, 1):
                    # Display appropriate score based on what's available
                    if 'relevance_score' in screenshot:
                        score_text = f"Relevance: {screenshot['relevance_score']:.3f}"
                        if 'original_distance' in screenshot:
                            score_text += f" (was distance: {screenshot['original_distance']:.3f})"
                    else:
                        score_text = f"Distance: {screenshot['distance']:.3f}"
                    
                    print(f"  {i}. {screenshot['path']} ({score_text})")
                    print(f"     Game: {screenshot['game_id']}")
                    print(f"     Caption: {screenshot['caption']}")
            else:
                print("  No screenshots found")
        
        # Test combined search
        print("\n🔄 Testing combined search...")
        combined_query = "progression achievements rewards"
        print(f"Query: '{combined_query}'")
        
        all_results = search_interface.search_all_game_content(query=combined_query, limit=6)
        
        print(f"Found {len(all_results['features'])} features and {len(all_results['screenshots'])} screenshots")
        
        if all_results['features']:
            print("Top features:")
            for feature in all_results['features'][:3]:
                # Display appropriate score
                if 'relevance_score' in feature:
                    score_text = f"Relevance: {feature['relevance_score']:.3f}"
                else:
                    score_text = f"Distance: {feature['distance']:.3f}"
                print(f"  - {feature['name']} ({score_text})")
        
        if all_results['screenshots']:
            print("Top screenshots:")
            for screenshot in all_results['screenshots'][:3]:
                # Display appropriate score
                if 'relevance_score' in screenshot:
                    score_text = f"Relevance: {screenshot['relevance_score']:.3f}"
                else:
                    score_text = f"Distance: {screenshot['distance']:.3f}"
                print(f"  - {screenshot['path']} ({score_text})")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_specific_game(game_id):
    """Test search for a specific game"""
    print(f"\n🎮 Testing search for game: {game_id}")
    
    search_interface = GameDataSearchInterface()
    
    # Test game-specific feature search
    features = search_interface.search_game_features(
        query="building construction", 
        limit=5, 
        game_id=game_id
    )
    
    print(f"Found {len(features)} features for game {game_id}")
    for feature in features:
        # Display appropriate score
        if 'relevance_score' in feature:
            score_text = f"Relevance: {feature['relevance_score']:.3f}"
        else:
            score_text = f"Distance: {feature['distance']:.3f}"
        print(f"  - {feature['name']} ({score_text})")

def test_reranking_specifically():
    """Test Cohere reranking specifically to see if it's working"""
    print("\n🔍 Testing Cohere Reranking Specifically...")
    
    # Test with reranking enabled
    print("\n1️⃣ Testing WITH reranking:")
    search_with_rerank = GameDataSearchInterface(use_reranking=True)
    results_with_rerank = search_with_rerank.search_game_features("building construction", limit=3)
    
    if results_with_rerank:
        for i, result in enumerate(results_with_rerank, 1):
            if 'relevance_score' in result:
                print(f"  {i}. {result['name']} - Relevance: {result['relevance_score']:.3f}")
                if 'original_distance' in result:
                    print(f"     (Original distance: {result['original_distance']:.3f})")
            else:
                print(f"  {i}. {result['name']} - Distance: {result['distance']:.3f} (NO RERANKING)")
    else:
        print("  No results found")
    
    # Test without reranking for comparison
    print("\n2️⃣ Testing WITHOUT reranking:")
    search_no_rerank = GameDataSearchInterface(use_reranking=False)
    results_no_rerank = search_no_rerank.search_game_features("building construction", limit=3)
    
    if results_no_rerank:
        for i, result in enumerate(results_no_rerank, 1):
            print(f"  {i}. {result['name']} - Distance: {result['distance']:.3f}")
    else:
        print("  No results found")
    
    # Analysis
    print("\n📊 Analysis:")
    if results_with_rerank and 'relevance_score' in results_with_rerank[0]:
        print("✅ Cohere reranking is WORKING")
        print("   - Results show 'relevance_score' (higher = better)")
        print("   - Results are reordered based on semantic relevance")
    else:
        print("❌ Cohere reranking is NOT working")
        print("   - Check your COHERE_API_KEY in .env.local")
        print("   - Results still showing 'distance' scores only")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ChromaDB vector search")
    parser.add_argument("--game-id", help="Test search for specific game ID")
    parser.add_argument("--test-reranking", action="store_true", help="Test Cohere reranking specifically")
    
    args = parser.parse_args()
    
    if args.test_reranking:
        # Run only the reranking test
        test_reranking_specifically()
    else:
        # Run main tests
        test_vector_search()
        
        # Run game-specific tests if requested
        if args.game_id:
            test_specific_game(args.game_id)

if __name__ == "__main__":
    main() 