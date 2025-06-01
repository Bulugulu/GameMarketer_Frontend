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
import json

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.feature_embeddings_generator import FeatureEmbeddingsGenerator
from ChromaDB.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator
from ChromaDB.chromadb_manager import ChromaDBManager

def setup_complete_vector_database(limit_features=None, limit_screenshots=None, game_id=None, use_existing_embeddings=False):
    """Complete setup of vector database system"""
    
    print("=== ChromaDB Vector Database Setup ===")
    
    feature_output = "ChromaDB/feature_embeddings.json"
    screenshot_output = "ChromaDB/screenshot_embeddings.json"
    
    if use_existing_embeddings:
        print("\n📁 Using existing embedding files...")
        
        # Check if files exist
        if not os.path.exists(feature_output):
            print(f"❌ Feature embeddings file not found: {feature_output}")
            print("   Run without --use-existing to generate new embeddings")
            return None
            
        if not os.path.exists(screenshot_output):
            print(f"❌ Screenshot embeddings file not found: {screenshot_output}")
            print("   Run without --use-existing to generate new embeddings")
            return None
            
        print(f"✓ Found existing feature embeddings: {feature_output}")
        print(f"✓ Found existing screenshot embeddings: {screenshot_output}")
        
        # Load metadata from existing files to show stats
        with open(feature_output, 'r', encoding='utf-8') as f:
            feature_data = json.load(f)
        with open(screenshot_output, 'r', encoding='utf-8') as f:
            screenshot_data = json.load(f)
            
        print(f"✓ Will reuse {feature_data['metadata']['successful_embeddings']} feature embeddings")
        print(f"✓ Will reuse {screenshot_data['metadata']['successful_embeddings']} screenshot embeddings")
        
    else:
        # Step 1: Generate feature embeddings
        print("\n1. Generating feature embeddings...")
        feature_generator = FeatureEmbeddingsGenerator()
        feature_embeddings = feature_generator.generate_all_feature_embeddings(
            limit=limit_features,
            game_id=game_id
        )
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
        screenshot_generator.save_embeddings_to_file(screenshot_embeddings, screenshot_output)
        print(f"✓ Generated {screenshot_embeddings['metadata']['successful_embeddings']} screenshot embeddings")
        print(f"✓ Used {screenshot_embeddings['metadata']['total_tokens']} tokens")
    
    # Step 3: Initialize ChromaDB (this will use cosine distance now)
    print(f"\n{'3' if use_existing_embeddings else '3'}. Setting up ChromaDB with cosine distance...")
    chroma_manager = ChromaDBManager(use_openai_embeddings=True)
    
    # Reset existing collections to apply new distance metric
    try:
        # Delete existing collections if they exist
        collections_to_delete = ["game_features", "game_screenshots"]
        for collection_name in collections_to_delete:
            try:
                chroma_manager.client.delete_collection(collection_name)
                print(f"✓ Deleted existing collection: {collection_name}")
            except:
                pass  # Collection might not exist
    except:
        pass
    
    # Create new collections with cosine distance
    chroma_manager.create_collections()
    print("✓ ChromaDB collections created with cosine distance")
    
    # Step 4: Load embeddings into ChromaDB
    print(f"\n{'4' if use_existing_embeddings else '4'}. Loading embeddings into vector database...")
    feature_count = chroma_manager.load_feature_embeddings_from_json(feature_output)
    screenshot_count = chroma_manager.load_screenshot_embeddings_from_json(screenshot_output)
    print(f"✓ Loaded {feature_count} features and {screenshot_count} screenshots")
    
    # Step 5: Verify setup
    print(f"\n{'5' if use_existing_embeddings else '5'}. Verifying setup...")
    db_info = chroma_manager.get_database_info()
    print(f"✓ Database path: {db_info['database_path']}")
    for collection in db_info['collections']:
        print(f"✓ {collection['name']}: {collection['count']} items")
    
    if not use_existing_embeddings:
        # Calculate total tokens used only if we generated new embeddings
        total_tokens = (feature_embeddings['metadata']['total_tokens'] + 
                       screenshot_embeddings['metadata']['total_tokens'])
        print(f"\n💰 Total OpenAI tokens used: {total_tokens:,}")
    else:
        print(f"\n💰 No new OpenAI tokens used (reused existing embeddings)")
    
    print("\n🎉 === Setup Complete with Cosine Distance ===")
    return chroma_manager

def main():
    parser = argparse.ArgumentParser(description="Setup complete ChromaDB vector database")
    parser.add_argument("--limit-features", type=int, help="Limit number of features to process")
    parser.add_argument("--limit-screenshots", type=int, help="Limit number of screenshots to process")
    parser.add_argument("--game-id", help="Process only specific game ID")
    parser.add_argument("--test", action="store_true", help="Run with small limits for testing")
    parser.add_argument("--use-existing", action="store_true", help="Use existing embeddings")
    
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
            game_id=args.game_id,
            use_existing_embeddings=args.use_existing
        )
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 