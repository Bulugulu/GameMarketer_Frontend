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

def setup_complete_vector_database(limit_features=None, limit_screenshots=None, game_id=None, use_existing_embeddings=False, rate_limit=0.1, dimensions=None, change_detection="content_hash", progress_every=10):
    """Complete setup of vector database system with speed optimization options"""
    
    print("=== ChromaDB Vector Database Setup ===")
    print(f"⚡ Rate limit: {rate_limit}s between API calls")
    if dimensions:
        print(f"🎯 Custom dimensions: {dimensions}")
    print(f"🔍 Change detection: {change_detection}")
    
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
        # Step 1: Generate feature embeddings with speed optimizations
        print("\n1. Generating feature embeddings...")
        feature_generator = FeatureEmbeddingsGenerator()
        
        # Configure speed settings
        feature_generator.rate_limit_delay = rate_limit
        
        feature_embeddings = feature_generator.generate_all_feature_embeddings(
            limit=limit_features,
            game_id=game_id,
            dimensions=dimensions,
            save_progress_every=progress_every,
            change_detection=change_detection
        )
        feature_generator.save_embeddings_to_file(feature_embeddings, feature_output)
        
        # Enhanced reporting
        metadata = feature_embeddings['metadata']
        print(f"✓ Generated {metadata['successful_embeddings']} feature embeddings")
        print(f"✓ Used {metadata['total_tokens']} tokens")
        print(f"✓ Processing time: {metadata.get('processing_time_seconds', 0):.1f} seconds")
        if metadata.get('new_features', 0) > 0 or metadata.get('changed_features', 0) > 0:
            print(f"✓ New: {metadata.get('new_features', 0)}, Changed: {metadata.get('changed_features', 0)}, Skipped: {metadata.get('unchanged_features', 0)}")
        
        # Step 2: Generate screenshot embeddings with speed optimizations
        print("\n2. Generating screenshot embeddings...")
        screenshot_generator = ScreenshotEmbeddingsGenerator()
        
        # Configure speed settings
        screenshot_generator.rate_limit_delay = rate_limit
        
        screenshot_embeddings = screenshot_generator.generate_all_screenshot_embeddings(
            limit=limit_screenshots,
            game_id=game_id,
            dimensions=dimensions,
            save_progress_every=progress_every,
            change_detection=change_detection
        )
        screenshot_generator.save_embeddings_to_file(screenshot_embeddings, screenshot_output)
        
        # Enhanced reporting
        metadata = screenshot_embeddings['metadata']
        print(f"✓ Generated {metadata['successful_embeddings']} screenshot embeddings")
        print(f"✓ Used {metadata['total_tokens']} tokens")
        print(f"✓ Processing time: {metadata.get('processing_time_seconds', 0):.1f} seconds")
        if metadata.get('new_screenshots', 0) > 0 or metadata.get('changed_screenshots', 0) > 0:
            print(f"✓ New: {metadata.get('new_screenshots', 0)}, Changed: {metadata.get('changed_screenshots', 0)}, Skipped: {metadata.get('unchanged_screenshots', 0)}")
    
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
        total_time = (feature_embeddings['metadata'].get('processing_time_seconds', 0) + 
                     screenshot_embeddings['metadata'].get('processing_time_seconds', 0))
        estimated_cost = total_tokens * 0.00013 / 1000  # $0.00013 per 1K tokens for text-embedding-3-large
        
        print(f"\n💰 Total OpenAI tokens used: {total_tokens:,}")
        print(f"⏱️  Total processing time: {total_time:.1f} seconds")
        print(f"💵 Estimated API cost: ${estimated_cost:.4f}")
        
        # Calculate effective rate
        total_embeddings = (feature_embeddings['metadata']['successful_embeddings'] + 
                          screenshot_embeddings['metadata']['successful_embeddings'])
        if total_time > 0:
            rate = total_embeddings / total_time
            print(f"⚡ Average processing rate: {rate:.1f} embeddings/second")
    else:
        print(f"\n💰 No new OpenAI tokens used (reused existing embeddings)")
    
    print("\n🎉 === Setup Complete with Enhanced Speed Optimization ===")
    return chroma_manager

def main():
    parser = argparse.ArgumentParser(description="Setup complete ChromaDB vector database with speed optimization")
    parser.add_argument("--limit-features", type=int, help="Limit number of features to process")
    parser.add_argument("--limit-screenshots", type=int, help="Limit number of screenshots to process")
    parser.add_argument("--game-id", help="Process only specific game ID")
    parser.add_argument("--test", action="store_true", help="Run with small limits for testing")
    parser.add_argument("--use-existing", action="store_true", help="Use existing embeddings")
    
    # Speed optimization options
    parser.add_argument("--rate-limit", type=float, default=0.1, 
                       help="Delay between API calls in seconds (default: 0.1). Lower = faster. Use 0.01 for paid accounts.")
    parser.add_argument("--dimensions", type=int, 
                       help="Custom embedding dimensions (1024-3072 for text-embedding-3-large). Lower = faster processing.")
    parser.add_argument("--change-detection", 
                       choices=["content_hash", "timestamp", "force_all", "skip_existing"], 
                       default="content_hash",
                       help="Method for detecting changed content (default: content_hash)")
    parser.add_argument("--progress-every", type=int, default=10, 
                       help="Show progress every N items (default: 10)")
    
    # Quick preset options
    parser.add_argument("--fast", action="store_true", 
                       help="Quick preset: --rate-limit 0.01 (good for paid accounts)")
    parser.add_argument("--max-speed", action="store_true", 
                       help="Maximum speed preset: --rate-limit 0 --dimensions 1536 (enterprise accounts)")
    
    args = parser.parse_args()
    
    # Handle presets
    if args.fast:
        args.rate_limit = 0.01
        print("🚀 Fast preset: Using 10ms rate limit (good for paid accounts)")
    elif args.max_speed:
        args.rate_limit = 0
        args.dimensions = args.dimensions or 1536
        print("🏎️ Maximum speed preset: No rate limit + reduced dimensions (enterprise accounts)")
    
    if args.test:
        print("🧪 Running in test mode with limited data...")
        limit_features = 10
        limit_screenshots = 10
    else:
        limit_features = args.limit_features
        limit_screenshots = args.limit_screenshots
    
    # Validate rate limit
    if args.rate_limit < 0:
        print("❌ Rate limit cannot be negative")
        sys.exit(1)
        
    # Validate dimensions
    if args.dimensions and (args.dimensions < 1024 or args.dimensions > 3072):
        print("❌ Dimensions must be between 1024 and 3072 for text-embedding-3-large")
        sys.exit(1)
    
    try:
        setup_complete_vector_database(
            limit_features=limit_features,
            limit_screenshots=limit_screenshots,
            game_id=args.game_id,
            use_existing_embeddings=args.use_existing,
            rate_limit=args.rate_limit,
            dimensions=args.dimensions,
            change_detection=args.change_detection,
            progress_every=args.progress_every
        )
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 