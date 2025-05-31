#!/usr/bin/env python3
"""
Script to generate feature embeddings from the PostgreSQL database

This script queries the features_game table from the database to get feature names and descriptions,
then generates embeddings using the OpenAI embedding model. It outputs a JSON file with the vector
embeddings and detailed analytics including field-level token statistics.

Usage:
    python generate_feature_embeddings.py [--limit <number>] [--output <filename>] [--dimensions <dims>]
    
Example:
    python generate_feature_embeddings.py --limit 10 --dimensions 1536 --output feature_embeddings.json
"""
import argparse
import logging
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.feature_embeddings_generator import FeatureEmbeddingsGenerator

# Set up logging for the script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('feature_embeddings_generation.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate feature embeddings with progress tracking and advanced analytics")
    parser.add_argument("--limit", type=int, help="Limit number of features (useful for testing)")
    parser.add_argument("--game_id", help="Specific game ID to process")
    parser.add_argument("--output", default="ChromaDB/feature_embeddings.json", help="Output filename")
    parser.add_argument("--dimensions", type=int, help="Embedding dimensions (1024-3072 for text-embedding-3-large, default: 3072)")
    parser.add_argument("--progress-every", type=int, default=10, help="Show progress every N features")
    parser.add_argument("--rate-limit", type=float, default=0.1, help="Delay between API calls (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume functionality (process all features, may create duplicates)")
    
    args = parser.parse_args()
    
    # Validate dimensions if provided
    if args.dimensions and (args.dimensions < 1024 or args.dimensions > 3072):
        logger.error("Dimensions must be between 1024 and 3072 for text-embedding-3-large")
        return 1
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Feature Embeddings Generation Started")
    logger.info("=" * 60)
    logger.info(f"Output file: {args.output}")
    logger.info(f"Limit: {args.limit or 'No limit'}")
    logger.info(f"Game ID filter: {args.game_id or 'All games'}")
    logger.info(f"Dimensions: {args.dimensions or 'Default (3072)'}")
    logger.info(f"Progress updates every: {args.progress_every} features")
    logger.info(f"Rate limit delay: {args.rate_limit}s")
    logger.info(f"Resume mode: {'Disabled' if args.no_resume else 'Enabled (will skip already processed features)'}")
    
    try:
        generator = FeatureEmbeddingsGenerator()
        
        # Set custom rate limit if specified
        generator.rate_limit_delay = args.rate_limit
        
        embeddings_data = generator.generate_all_feature_embeddings(
            limit=args.limit, 
            game_id=args.game_id,
            save_progress_every=args.progress_every,
            dimensions=args.dimensions,
            resume=not args.no_resume  # Resume is enabled by default, disabled if --no-resume is passed
        )
        
        generator.save_embeddings_to_file(embeddings_data, args.output)
        
        # Enhanced summary
        metadata = embeddings_data['metadata']
        logger.info("GENERATION COMPLETE - SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✓ Output file: {args.output}")
        logger.info(f"✓ Model: {metadata['model']}")
        logger.info(f"✓ Dimensions: {metadata.get('dimensions', 'default (3072)')}")
        logger.info(f"✓ Total features in database: {metadata.get('total_features_in_db', metadata.get('total_features', 0))}")
        
        # Show resume statistics if applicable
        if metadata.get('skipped_features', 0) > 0:
            logger.info(f"✓ Features skipped (already processed): {metadata['skipped_features']}")
            logger.info(f"✓ New features processed: {metadata.get('new_features_to_process', 0)}")
        else:
            logger.info(f"✓ Features processed: {metadata.get('new_features_to_process', metadata.get('total_features', 0))}")
            
        logger.info(f"✓ Successful embeddings: {metadata.get('successful_embeddings', 0)}")
        logger.info(f"✓ Failed embeddings: {metadata.get('failed_embeddings', 0)}")
        logger.info(f"✓ Success rate: {metadata.get('success_rate', 0):.1f}%")
        logger.info(f"✓ Total tokens used: {metadata['total_tokens']:,}")
        logger.info(f"✓ Average tokens per embedding: {metadata.get('avg_tokens_per_embedding', 0)}")
        logger.info(f"✓ Processing time: {metadata.get('processing_time_seconds', 0):.1f} seconds")
        
        # Cost estimation (approximate)
        estimated_cost = metadata['total_tokens'] * 0.00013 / 1000  # $0.00013 per 1K tokens for text-embedding-3-large
        logger.info(f"✓ Estimated API cost: ${estimated_cost:.4f}")
        
        # Field-level statistics
        field_stats = metadata.get('field_token_stats', {})
        if any(stats['count'] > 0 for stats in field_stats.values()):
            logger.info(f"\n--- Field Token Statistics ---")
            for field, stats in field_stats.items():
                if stats['count'] > 0:
                    logger.info(f"✓ {field.capitalize()}: {stats['total']} total tokens, {stats['count']} fields, {stats['avg']} avg tokens/field")
        
        if metadata.get('failed_embeddings', 0) > 0:
            logger.warning(f"⚠️  {metadata['failed_embeddings']} features failed to generate embeddings")
            logger.warning("   Check the logs above for specific error details")
        
        logger.info("=" * 60)
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Generation interrupted by user (Ctrl+C)")
        logger.info("Partial results may be saved. Check the output file.")
        return 1
        
    except Exception as e:
        logger.error(f"Generation failed with error: {str(e)}")
        logger.exception("Full error details:")
        return 1

if __name__ == "__main__":
    exit(main()) 