#!/usr/bin/env python3
"""
Complete setup script for the ChromaDB vector database system
This script will:
1. Generate feature embeddings
2. Generate screenshot embeddings  
3. Initialize ChromaDB
4. Load embeddings into ChromaDB
5. Verify the setup
"""
import os
import sys
import argparse

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.feature_embeddings_generator import FeatureEmbeddingsGenerator
from ChromaDB.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator
from ChromaDB.chromadb_manager import ChromaDBManager

def setup_complete_vector_database(limit_features=None, limit_screenshots=None, game_id=None):
    """Complete setup of vector database system"""
    
    print("=== ChromaDB Vector Database Setup ===")
    
    # Step 1: Generate feature embeddings
    print("\n1. Generating feature embeddings...")
    feature_generator = FeatureEmbeddingsGenerator()
    feature_embeddings = feature_generator.generate_all_feature_embeddings(
        limit=limit_features,
        game_id=game_id
    )
    feature_output = "ChromaDB/feature_embeddings.json"
    feature_generator.save_embeddings_to_file(feature_embeddings, feature_output)
    print(f"✓ Generated {feature_embeddings['metadata']['successful_embeddings']} feature embeddings")
    print(f"✓ Used {feature_embeddings['metadata']['total_tokens']} tokens")
    
    # Step 2: Generate screenshot embeddings
    print("\n2. Generating screenshot embeddings...")
    screenshot_generator = ScreenshotEmbeddingsGenerator()
    screenshot_embeddings = screenshot_generator.generate_all_screenshot_embeddings(
        limit=limit_screenshots,
        game_id=game_id
    )
    screenshot_output = "ChromaDB/screenshot_embeddings.json"
    screenshot_generator.save_embeddings_to_file(screenshot_embeddings, screenshot_output)
    print(f"✓ Generated {screenshot_embeddings['metadata']['successful_embeddings']} screenshot embeddings")
    print(f"✓ Used {screenshot_embeddings['metadata']['total_tokens']} tokens")
    
    # Step 3: Initialize ChromaDB
    print("\n3. Setting up ChromaDB...")
    chroma_manager = ChromaDBManager(use_openai_embeddings=True)
    chroma_manager.create_collections()
    print("✓ ChromaDB collections created")
    
    # Step 4: Load embeddings into ChromaDB
    print("\n4. Loading embeddings into vector database...")
    feature_count = chroma_manager.load_feature_embeddings_from_json(feature_output)
    screenshot_count = chroma_manager.load_screenshot_embeddings_from_json(screenshot_output)
    print(f"✓ Loaded {feature_count} features and {screenshot_count} screenshots")
    
    # Step 5: Verify setup
    print("\n5. Verifying setup...")
    db_info = chroma_manager.get_database_info()
    print(f"✓ Database path: {db_info['database_path']}")
    for collection in db_info['collections']:
        print(f"✓ {collection['name']}: {collection['count']} items")
    
    # Calculate total tokens used
    total_tokens = (feature_embeddings['metadata']['total_tokens'] + 
                   screenshot_embeddings['metadata']['total_tokens'])
    print(f"\n💰 Total OpenAI tokens used: {total_tokens:,}")
    
    print("\n🎉 === Setup Complete ===")
    return chroma_manager

def main():
    parser = argparse.ArgumentParser(description="Setup complete ChromaDB vector database")
    parser.add_argument("--limit-features", type=int, help="Limit number of features to process")
    parser.add_argument("--limit-screenshots", type=int, help="Limit number of screenshots to process")
    parser.add_argument("--game-id", help="Process only specific game ID")
    parser.add_argument("--test", action="store_true", help="Run with small limits for testing")
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Running in test mode with limited data...")
        limit_features = 10
        limit_screenshots = 10
    else:
        limit_features = args.limit_features
        limit_screenshots = args.limit_screenshots
    
    try:
        setup_complete_vector_database(
            limit_features=limit_features,
            limit_screenshots=limit_screenshots,
            game_id=args.game_id
        )
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 