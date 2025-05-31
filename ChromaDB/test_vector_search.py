#!/usr/bin/env python3
"""
Test script for the ChromaDB vector search system
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.vector_search_interface import GameDataSearchInterface

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
        for collection in stats['collections']:
            print(f"- {collection['name']}: {collection['count']} items")
        
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
                    print(f"  {i}. {feature['name']} (Distance: {feature['distance']:.3f})")
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
                    print(f"  {i}. {screenshot['path']} (Distance: {screenshot['distance']:.3f})")
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
                print(f"  - {feature['name']} (Distance: {feature['distance']:.3f})")
        
        if all_results['screenshots']:
            print("Top screenshots:")
            for screenshot in all_results['screenshots'][:3]:
                print(f"  - {screenshot['path']} (Distance: {screenshot['distance']:.3f})")
        
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
        print(f"  - {feature['name']} (Distance: {feature['distance']:.3f})")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ChromaDB vector search")
    parser.add_argument("--game-id", help="Test search for specific game ID")
    
    args = parser.parse_args()
    
    # Run main tests
    test_vector_search()
    
    # Run game-specific tests if requested
    if args.game_id:
        test_specific_game(args.game_id)

if __name__ == "__main__":
    main() 