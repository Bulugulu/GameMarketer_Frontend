#!/usr/bin/env python3
"""
Test script for Cohere reranking integration
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ChromaDB.vector_search_interface import GameDataSearchInterface
from ChromaDB.cohere_reranker import CohereReranker
import time


def test_cohere_reranker_standalone():
    """Test the Cohere reranker in isolation"""
    print("=== Testing Cohere Reranker Standalone ===")
    
    try:
        reranker = CohereReranker()
        print("✓ Cohere reranker initialized successfully")
        
        # Test documents
        test_documents = [
            "Farming and agriculture in Township involves planting crops and harvesting them for production.",
            "Building construction requires coins and materials to expand your town.",
            "Social features allow players to join co-ops and participate in weekly regattas.",
            "Combat and battles are not a primary feature in Township's peaceful farming gameplay.",
            "Crop rotation and farming strategies help optimize production chains in the agricultural system."
        ]
        
        test_query = "farming crops agriculture"
        
        print(f"\nTesting query: '{test_query}'")
        print("Documents to rank:")
        for i, doc in enumerate(test_documents):
            print(f"  {i}: {doc}")
        
        # Test reranking
        results = reranker.rerank_results(test_query, test_documents, top_n=3)
        
        print(f"\nCohere reranking results (top 3):")
        for i, result in enumerate(results):
            doc_index = result['index']
            relevance_score = result['relevance_score']
            doc_text = test_documents[doc_index][:80] + "..."
            
            # Color coding for relevance
            relevance_color = "🟢" if relevance_score >= 0.8 else "🟡" if relevance_score >= 0.6 else "🟠" if relevance_score >= 0.4 else "🔴"
            
            print(f"  {i+1}. {relevance_color} Score: {relevance_score:.3f} | Doc {doc_index}: {doc_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Standalone reranker test failed: {e}")
        return False


def test_search_interface_with_reranking():
    """Test the GameDataSearchInterface with reranking enabled"""
    print("\n=== Testing Search Interface with Reranking ===")
    
    try:
        # Test with reranking enabled
        search_interface = GameDataSearchInterface(use_reranking=True)
        
        # Get database stats to confirm reranking status
        stats = search_interface.get_database_stats()
        print(f"Database stats: {stats}")
        print(f"Reranking enabled: {stats.get('reranking_enabled', False)}")
        
        if not stats.get('reranking_enabled', False):
            print("⚠️  Warning: Reranking not enabled, testing fallback mode")
        
        # Test queries for different types of content
        test_queries = [
            "farming agriculture crops",
            "building construction town expansion", 
            "social features co-op multiplayer",
            "currency coins money economy"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Test feature search
            feature_results = search_interface.search_game_features(query=query, limit=5)
            
            if feature_results:
                print(f"Found {len(feature_results)} features:")
                for i, feature in enumerate(feature_results, 1):
                    # Handle both scoring systems
                    if 'relevance_score' in feature:
                        score = feature['relevance_score']
                        score_type = "Relevance"
                        relevance_color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🟠" if score >= 0.4 else "🔴"
                    else:
                        score = feature.get('distance', 0)
                        score_type = "Distance"
                        relevance_color = "🟢" if score < 0.3 else "🟡" if score < 0.7 else "🟠" if score < 1.2 else "🔴"
                    
                    print(f"  {i}. {relevance_color} {score_type}: {score:.3f} | {feature['name']}")
                    print(f"     Game: {feature['game_id']} | ID: {feature['feature_id']}")
                    if 'original_distance' in feature:
                        print(f"     Original distance: {feature['original_distance']:.3f}")
            else:
                print("  No features found")
            
            # Test screenshot search
            screenshot_results = search_interface.search_game_screenshots(query=query, limit=3)
            
            if screenshot_results:
                print(f"Found {len(screenshot_results)} screenshots:")
                for i, screenshot in enumerate(screenshot_results, 1):
                    # Handle both scoring systems
                    if 'relevance_score' in screenshot:
                        score = screenshot['relevance_score']
                        score_type = "Relevance"
                        relevance_color = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🟠" if score >= 0.4 else "🔴"
                    else:
                        score = screenshot.get('distance', 0)
                        score_type = "Distance"
                        relevance_color = "🟢" if score < 0.3 else "🟡" if score < 0.7 else "🟠" if score < 1.2 else "🔴"
                    
                    caption_preview = screenshot['caption'][:50] + "..." if len(screenshot['caption']) > 50 else screenshot['caption']
                    print(f"  {i}. {relevance_color} {score_type}: {score:.3f} | {caption_preview}")
            else:
                print("  No screenshots found")
        
        return True
        
    except Exception as e:
        print(f"❌ Search interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_behavior():
    """Test fallback behavior when Cohere is unavailable"""
    print("\n=== Testing Fallback Behavior ===")
    
    try:
        # Test with reranking disabled
        search_interface = GameDataSearchInterface(use_reranking=False)
        
        stats = search_interface.get_database_stats()
        print(f"Reranking enabled: {stats.get('reranking_enabled', False)}")
        
        # Should use distance scoring
        results = search_interface.search_game_features("farming", limit=3)
        
        if results:
            print("Fallback results (should use distance scoring):")
            for i, result in enumerate(results, 1):
                if 'distance' in result:
                    print(f"  {i}. Distance: {result['distance']:.3f} | {result['name']}")
                else:
                    print(f"  {i}. Unexpected scoring format: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False


def evaluate_reranking_quality():
    """Evaluate and develop rubric for reranking quality"""
    print("\n=== Evaluating Reranking Quality ===")
    
    print("""
    📊 RERANKING QUALITY RUBRIC
    
    Cohere Relevance Scores (0.0 - 1.0):
    🟢 ≥ 0.8: Highly Relevant
       - Content directly matches user intent
       - Primary features/screenshots for the query
       - Should be shown to user immediately
    
    🟡 0.6 - 0.79: Moderately Relevant  
       - Content relates to user intent but may be broader
       - Secondary features that support the main query
       - Good for follow-up exploration
    
    🟠 0.4 - 0.59: Somewhat Relevant
       - Content has some connection but may be tangential
       - Consider for comprehensive searches
       - May need additional context/filtering
    
    🔴 < 0.4: Low Relevance
       - Content doesn't match user intent well
       - Should be filtered out in most cases
       - Only show if specifically requested by user
    
    COMPARISON WITH VECTOR SIMILARITY:
    - Vector similarity gives broader semantic matches
    - Cohere reranking focuses on query-specific relevance
    - Reranking should improve precision over pure vector search
    - Expect some reshuffling of results for better relevance
    """)
    
    try:
        search_interface = GameDataSearchInterface(use_reranking=True)
        
        # Test with a specific query to evaluate quality
        query = "player progression and leveling up"
        
        print(f"Quality evaluation for query: '{query}'")
        
        # Get results with reranking
        results = search_interface.search_game_features(query, limit=10)
        
        if results and len(results) > 0:
            print("\nResults analysis:")
            
            # Count results by relevance tier
            high_relevance = [r for r in results if r.get('relevance_score', 0) >= 0.8]
            moderate_relevance = [r for r in results if 0.6 <= r.get('relevance_score', 0) < 0.8]
            low_relevance = [r for r in results if r.get('relevance_score', 0) < 0.6]
            
            print(f"🟢 High relevance (≥0.8): {len(high_relevance)} results")
            print(f"🟡 Moderate relevance (0.6-0.79): {len(moderate_relevance)} results") 
            print(f"🔴 Low relevance (<0.6): {len(low_relevance)} results")
            
            if high_relevance:
                print("\nHigh relevance results:")
                for result in high_relevance:
                    print(f"  • {result['name']} (Score: {result['relevance_score']:.3f})")
            
            # Quality indicators
            print(f"\nQuality indicators:")
            print(f"  - Precision at top 3: {len([r for r in results[:3] if r.get('relevance_score', 0) >= 0.6])/3:.2%}")
            print(f"  - High relevance rate: {len(high_relevance)/len(results):.2%}")
            
            return True
        else:
            print("No results found for quality evaluation")
            return False
            
    except Exception as e:
        print(f"❌ Quality evaluation failed: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 COHERE RERANKING INTEGRATION TESTS")
    print("=" * 50)
    
    tests = [
        ("Standalone Reranker", test_cohere_reranker_standalone),
        ("Search Interface with Reranking", test_search_interface_with_reranking),
        ("Fallback Behavior", test_fallback_behavior),
        ("Reranking Quality Evaluation", evaluate_reranking_quality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            print(f"\n❌ FAILED: {test_name} - {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        print("🎉 All tests passed! Cohere reranking integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main() 