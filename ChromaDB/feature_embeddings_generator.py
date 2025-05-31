import json
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from .database_connection import DatabaseConnection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeatureEmbeddingsGenerator:
    def __init__(self):
        self.db = DatabaseConnection()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.rate_limit_delay = 0.1  # 100ms delay between API calls to respect rate limits
        self._validate_environment()
        
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ["PG_USER", "PG_PASSWORD", "PG_HOST", "PG_DATABASE", "OPENAI_API_KEY"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info("✓ All required environment variables validated")
        
    def query_features_from_database(self, limit=None, game_id=None):
        """Query features from PostgreSQL database"""
        logger.info(f"Querying features from database (limit: {limit}, game_id: {game_id})")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if game_id:
            query = """
                SELECT feature_id, name, description, game_id 
                FROM features_game 
                WHERE game_id = %s
                ORDER BY feature_id
            """
            params = (game_id,)
        else:
            query = """
                SELECT feature_id, name, description, game_id 
                FROM features_game 
                ORDER BY feature_id
            """
            params = ()
            
        if limit:
            query += " LIMIT %s"
            params = params + (limit,)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        features = []
        for row in results:
            feature_id, name, description, game_id = row
            features.append({
                "feature_id": feature_id,
                "name": name or "",
                "description": description or "",
                "game_id": str(game_id) if game_id else ""
            })
        
        logger.info(f"Retrieved {len(features)} features from database")
        return features
    
    def combine_feature_text(self, feature):
        """Combine name and description for embedding using improved format"""
        text_parts = []
        
        if feature.get("name"):
            text_parts.append(feature["name"])
        if feature.get("description"):
            text_parts.append(feature["description"])
        
        # Use "Name: Description" format for better readability
        if len(text_parts) == 2:
            return f"{text_parts[0]}: {text_parts[1]}"
        elif len(text_parts) == 1:
            return text_parts[0]
        else:
            return f"Feature {feature.get('feature_id', 'unknown')}"
    
    def calculate_field_tokens(self, feature):
        """Calculate estimated tokens for each field separately"""
        tokens = {
            "name": 0,
            "description": 0
        }
        
        # Rough estimation: ~4 characters per token
        if feature.get("name"):
            tokens["name"] = max(1, len(feature["name"]) // 4)
            
        if feature.get("description"):
            tokens["description"] = max(1, len(feature["description"]) // 4)
            
        return tokens
    
    def get_existing_feature_ids(self):
        """Get list of feature IDs already in ChromaDB"""
        try:
            from .chromadb_manager import ChromaDBManager
            chroma_manager = ChromaDBManager()
            
            # Try to get the collection, create it if it doesn't exist
            try:
                collection = chroma_manager.client.get_collection("game_features")
            except Exception:
                # Collection doesn't exist yet, no existing features
                logger.info("ChromaDB collection 'game_features' doesn't exist yet - starting fresh")
                return set()
            
            # Get all existing IDs
            try:
                results = collection.get()
                existing_ids = set()
                
                if results and 'ids' in results:
                    for doc_id in results['ids']:
                        # Extract feature_id from "feature_123" format
                        if doc_id.startswith('feature_'):
                            try:
                                feature_id = int(doc_id.replace('feature_', ''))
                                existing_ids.add(feature_id)
                            except ValueError:
                                continue
                
                logger.info(f"Found {len(existing_ids)} existing features in ChromaDB")
                return existing_ids
                
            except Exception as e:
                logger.warning(f"Could not retrieve existing features: {e}")
                return set()
                
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}")
            return set()
    
    def generate_embedding_for_text(self, text, retries=3, dimensions=None):
        """Generate OpenAI embedding for text with retry logic and custom dimensions"""
        for attempt in range(retries):
            try:
                # Add rate limiting delay
                if attempt > 0:
                    time.sleep(self.rate_limit_delay * (2 ** attempt))  # Exponential backoff
                
                # Prepare embedding parameters
                embed_params = {
                    "model": "text-embedding-3-large",
                    "input": text,
                    "encoding_format": "float"
                }
                
                # Add custom dimensions if specified
                if dimensions:
                    embed_params["dimensions"] = dimensions
                
                response = self.client.embeddings.create(**embed_params)
                
                return {
                    "embedding": response.data[0].embedding,
                    "success": True,
                    "model": "text-embedding-3-large",
                    "dimensions": dimensions,
                    "attempts": attempt + 1,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            except Exception as e:
                logger.warning(f"Embedding generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == retries - 1:  # Last attempt
                    return {
                        "embedding": [],
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1,
                        "dimensions": dimensions
                    }
                # Wait before retry
                time.sleep(1 * (attempt + 1))
        
        return {
            "embedding": [],
            "success": False,
            "error": "All retry attempts failed",
            "attempts": retries,
            "dimensions": dimensions
        }
    
    def generate_all_feature_embeddings(self, limit=None, game_id=None, save_progress_every=10, dimensions=None, resume=True):
        """Generate embeddings for all features with progress tracking and enhanced analytics"""
        # Validate dimensions if specified
        if dimensions and (dimensions < 1024 or dimensions > 3072):
            raise ValueError("Dimensions must be between 1024 and 3072 for text-embedding-3-large")
        
        features = self.query_features_from_database(limit, game_id)
        
        if not features:
            logger.warning("No features found in database")
            return {
                "metadata": {
                    "total_features": 0,
                    "model": "text-embedding-3-large",
                    "dimensions": dimensions,
                    "generated_at": datetime.now().isoformat(),
                    "successful_embeddings": 0,
                    "failed_embeddings": 0,
                    "total_tokens": 0,
                    "avg_tokens_per_embedding": 0.0,
                    "field_token_stats": {
                        "name": {"total": 0, "count": 0, "avg": 0.0},
                        "description": {"total": 0, "count": 0, "avg": 0.0}
                    }
                },
                "features": []
            }
        
        original_count = len(features)
        
        # Resume functionality - skip already processed features
        if resume:
            existing_ids = self.get_existing_feature_ids()
            if existing_ids:
                features = [f for f in features if f['feature_id'] not in existing_ids]
                skipped_count = original_count - len(features)
                
                if skipped_count > 0:
                    logger.info(f"🔄 Resume mode: Skipping {skipped_count} already processed features")
                    logger.info(f"📊 Processing {len(features)} remaining features ({len(features)}/{original_count})")
                else:
                    logger.info("✅ All features already processed!")
                    if len(features) == 0:
                        # Return early if nothing to process
                        return {
                            "metadata": {
                                "total_features_in_db": original_count,
                                "skipped_features": skipped_count,
                                "new_features": 0,
                                "model": "text-embedding-3-large",
                                "dimensions": dimensions,
                                "generated_at": datetime.now().isoformat(),
                                "successful_embeddings": 0,
                                "failed_embeddings": 0,
                                "total_tokens": 0,
                                "avg_tokens_per_embedding": 0.0,
                                "field_token_stats": {
                                    "name": {"total": 0, "count": 0, "avg": 0.0},
                                    "description": {"total": 0, "count": 0, "avg": 0.0}
                                }
                            },
                            "features": []
                        }
            else:
                logger.info("🆕 No existing features found - processing all features")
                skipped_count = 0
        else:
            logger.info("⚠️  Resume disabled - processing all features (may create duplicates)")
            skipped_count = 0

        embeddings_data = {
            "metadata": {
                "total_features_in_db": original_count,
                "skipped_features": skipped_count,
                "new_features_to_process": len(features),
                "model": "text-embedding-3-large",
                "dimensions": dimensions,
                "generated_at": datetime.now().isoformat(),
                "successful_embeddings": 0,
                "failed_embeddings": 0,
                "total_tokens": 0,
                "avg_tokens_per_embedding": 0.0,
                "field_token_stats": {
                    "name": {"total": 0, "count": 0, "avg": 0.0},
                    "description": {"total": 0, "count": 0, "avg": 0.0}
                }
            },
            "features": []
        }
        
        start_time = time.time()
        
        logger.info(f"Starting embedding generation for {len(features)} features")
        if dimensions:
            logger.info(f"Using custom dimensions: {dimensions}")
        
        for i, feature in enumerate(features, 1):
            logger.info(f"Processing feature {i}/{len(features)} (ID: {feature['feature_id']}): {feature.get('name', 'Unnamed')[:50]}...")
            
            combined_text = self.combine_feature_text(feature)
            field_tokens = self.calculate_field_tokens(feature)
            
            if not combined_text.strip():
                logger.warning(f"Feature {feature['feature_id']} has no text content, skipping embedding generation")
                feature_data = {
                    **feature,
                    "combined_text": combined_text,
                    "embedding": [],
                    "embedding_dimension": 0,
                    "success": False,
                    "error": "No text content to embed",
                    "token_breakdown": field_tokens,
                    "actual_tokens": 0,
                    "dimensions": dimensions
                }
                embeddings_data["metadata"]["failed_embeddings"] += 1
            else:
                embedding_result = self.generate_embedding_for_text(combined_text, dimensions=dimensions)
                
                feature_data = {
                    **feature,
                    "combined_text": combined_text,
                    "embedding": embedding_result["embedding"],
                    "embedding_dimension": len(embedding_result["embedding"]) if embedding_result["embedding"] else 0,
                    "success": embedding_result["success"],
                    "model": embedding_result.get("model", ""),
                    "dimensions": embedding_result.get("dimensions"),
                    "attempts": embedding_result.get("attempts", 1),
                    "token_breakdown": field_tokens
                }
                
                if embedding_result["success"]:
                    embeddings_data["metadata"]["successful_embeddings"] += 1
                    
                    # Use actual tokens from OpenAI
                    if "usage" in embedding_result:
                        actual_tokens = embedding_result["usage"]["prompt_tokens"]
                        embeddings_data["metadata"]["total_tokens"] += actual_tokens
                        feature_data["actual_tokens"] = actual_tokens
                        feature_data["usage"] = embedding_result["usage"]
                    else:
                        # Fallback to estimation
                        estimated_tokens = len(combined_text) // 4
                        embeddings_data["metadata"]["total_tokens"] += estimated_tokens
                        feature_data["actual_tokens"] = estimated_tokens
                    
                    # Update field-level statistics
                    for field, token_count in field_tokens.items():
                        if token_count > 0:
                            embeddings_data["metadata"]["field_token_stats"][field]["total"] += token_count
                            embeddings_data["metadata"]["field_token_stats"][field]["count"] += 1
                    
                    logger.debug(f"✓ Feature {feature['feature_id']} embedded successfully ({feature_data.get('actual_tokens', 0)} tokens)")
                else:
                    embeddings_data["metadata"]["failed_embeddings"] += 1
                    feature_data["error"] = embedding_result["error"]
                    feature_data["actual_tokens"] = 0
                    logger.error(f"✗ Feature {feature['feature_id']} embedding failed: {embedding_result['error']}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
            
            embeddings_data["features"].append(feature_data)
            
            # Progress update every N features
            if i % save_progress_every == 0 or i == len(features):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(features) - i) / rate if rate > 0 else 0
                
                logger.info(f"Progress: {i}/{len(features)} ({(i/len(features)*100):.1f}%) | "
                          f"Success: {embeddings_data['metadata']['successful_embeddings']} | "
                          f"Failed: {embeddings_data['metadata']['failed_embeddings']} | "
                          f"Rate: {rate:.1f} features/sec | ETA: {eta:.0f}s")
        
        # Calculate final statistics
        if embeddings_data["metadata"]["successful_embeddings"] > 0:
            embeddings_data["metadata"]["avg_tokens_per_embedding"] = round(
                embeddings_data["metadata"]["total_tokens"] / embeddings_data["metadata"]["successful_embeddings"], 2
            )
            
            # Calculate field averages
            for field in embeddings_data["metadata"]["field_token_stats"]:
                field_stats = embeddings_data["metadata"]["field_token_stats"][field]
                if field_stats["count"] > 0:
                    field_stats["avg"] = round(field_stats["total"] / field_stats["count"], 2)
        
        embeddings_data["metadata"]["processing_time_seconds"] = time.time() - start_time
        embeddings_data["metadata"]["success_rate"] = (
            embeddings_data["metadata"]["successful_embeddings"] / len(features) * 100
        )
        
        logger.info(f"Embedding generation completed!")
        logger.info(f"  Total features: {len(features)}")
        logger.info(f"  Successful: {embeddings_data['metadata']['successful_embeddings']}")
        logger.info(f"  Failed: {embeddings_data['metadata']['failed_embeddings']}")
        logger.info(f"  Success rate: {embeddings_data['metadata']['success_rate']:.1f}%")
        logger.info(f"  Total tokens: {embeddings_data['metadata']['total_tokens']}")
        logger.info(f"  Avg tokens per embedding: {embeddings_data['metadata']['avg_tokens_per_embedding']}")
        logger.info(f"  Processing time: {embeddings_data['metadata']['processing_time_seconds']:.1f}s")
        
        # Log field statistics
        field_stats = embeddings_data["metadata"]["field_token_stats"]
        logger.info(f"  Field Token Statistics:")
        for field, stats in field_stats.items():
            if stats['count'] > 0:
                logger.info(f"    {field.capitalize()}: {stats['total']} total, {stats['count']} fields, {stats['avg']} avg tokens/field")
        
        return embeddings_data
    
    def save_embeddings_to_file(self, embeddings_data, output_file):
        """Save embeddings to JSON file with enhanced logging"""
        logger.info(f"Saving embeddings to {output_file}")
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ Embeddings saved successfully to {output_file}")
            
            # Log file size and summary
            file_size = os.path.getsize(output_file)
            logger.info(f"  File size: {file_size / (1024*1024):.1f} MB")
            
            # Print detailed summary
            metadata = embeddings_data['metadata']
            logger.info(f"\n=== FINAL SUMMARY ===")
            logger.info(f"Model: {metadata['model']}")
            logger.info(f"Dimensions: {metadata.get('dimensions', 'default (3072)')}")
            logger.info(f"Total features processed: {metadata['total_features_in_db']}")
            logger.info(f"Successful embeddings: {metadata['successful_embeddings']}")
            logger.info(f"Failed embeddings: {metadata['failed_embeddings']}")
            logger.info(f"Success rate: {metadata.get('success_rate', 0):.1f}%")
            logger.info(f"Total tokens used: {metadata['total_tokens']}")
            logger.info(f"Average tokens per embedding: {metadata.get('avg_tokens_per_embedding', 0)}")
            
        except Exception as e:
            logger.error(f"✗ Failed to save embeddings: {str(e)}")
            raise 