import json
import os
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional, Set, Tuple
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
        """Query features from PostgreSQL database with optional timestamps for change detection"""
        logger.info(f"Querying features from database (limit: {limit}, game_id: {game_id})")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Check if timestamp columns exist in the table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'features_game' 
            AND column_name IN ('created_at', 'updated_at', 'last_updated')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        has_created_at = 'created_at' in existing_columns
        has_updated_at = 'updated_at' in existing_columns
        has_last_updated = 'last_updated' in existing_columns
        
        # Build query based on available columns
        base_fields = "feature_id, name, description, game_id"
        timestamp_fields = []
        
        if has_created_at:
            timestamp_fields.append("created_at")
        if has_updated_at:
            timestamp_fields.append("updated_at")
        elif has_last_updated:
            timestamp_fields.append("last_updated")
        
        if timestamp_fields:
            fields = f"{base_fields}, {', '.join(timestamp_fields)}"
            logger.debug(f"Database has timestamp columns: {timestamp_fields}")
        else:
            fields = base_fields
            logger.info("Database does not have timestamp columns - using content-only change detection")
        
        if game_id:
            query = f"""
                SELECT {fields}
                FROM features_game 
                WHERE game_id = %s
                ORDER BY feature_id
            """
            params = (game_id,)
        else:
            query = f"""
                SELECT {fields}
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
            # Unpack based on available columns
            feature_id = row[0]
            name = row[1]
            description = row[2]
            game_id = row[3]
            
            feature_data = {
                "feature_id": feature_id,
                "name": name or "",
                "description": description or "",
                "game_id": str(game_id) if game_id else ""
            }
            
            # Add timestamp fields if available
            col_index = 4
            if has_created_at:
                created_at = row[col_index] if len(row) > col_index else None
                feature_data["created_at"] = created_at.isoformat() if created_at else None
                col_index += 1
            
            if has_updated_at:
                updated_at = row[col_index] if len(row) > col_index else None
                feature_data["updated_at"] = updated_at.isoformat() if updated_at else None
                col_index += 1
            elif has_last_updated:
                last_updated = row[col_index] if len(row) > col_index else None
                # Map last_updated to updated_at for consistency in the rest of the code
                feature_data["updated_at"] = last_updated.isoformat() if last_updated else None
                feature_data["last_updated"] = last_updated.isoformat() if last_updated else None
                col_index += 1
            
            # If no timestamps available, use None (content hash method will still work)
            if not has_created_at:
                feature_data["created_at"] = None
            if not has_updated_at and not has_last_updated:
                feature_data["updated_at"] = None
                
            features.append(feature_data)
        
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
    
    def calculate_content_hash(self, feature):
        """Calculate hash of feature content for change detection"""
        # Combine the fields that affect embeddings for hashing
        content_parts = [
            feature.get("name", ""),
            feature.get("description", "")
        ]
        content_string = "|".join(content_parts)
        return hashlib.sha256(content_string.encode('utf-8')).hexdigest()[:16]  # First 16 chars for brevity
    
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
    
    def get_existing_features_with_metadata(self):
        """Get existing features from ChromaDB with their content hashes and metadata"""
        try:
            from .chromadb_manager import ChromaDBManager
            chroma_manager = ChromaDBManager()
            
            # Try to get the collection, create it if it doesn't exist
            try:
                collection = chroma_manager.client.get_collection("game_features")
            except Exception:
                # Collection doesn't exist yet, no existing features
                logger.info("ChromaDB collection 'game_features' doesn't exist yet - starting fresh")
                return {}
            
            # Get all existing documents with metadata
            try:
                results = collection.get(include=['metadatas'])
                existing_features = {}
                
                if results and 'ids' in results and 'metadatas' in results:
                    for doc_id, metadata in zip(results['ids'], results['metadatas']):
                        # Extract feature_id from "feature_123" format
                        if doc_id.startswith('feature_'):
                            try:
                                feature_id = int(doc_id.replace('feature_', ''))
                                existing_features[feature_id] = {
                                    'id': doc_id,
                                    'content_hash': metadata.get('content_hash', ''),
                                    'last_updated': metadata.get('last_updated', ''),
                                    'name': metadata.get('name', ''),
                                    'description': metadata.get('description', ''),
                                    'embedding_generated_at': metadata.get('embedding_generated_at', '')
                                }
                            except ValueError:
                                continue
                
                logger.info(f"Found {len(existing_features)} existing features in ChromaDB with metadata")
                return existing_features
                
            except Exception as e:
                logger.warning(f"Could not retrieve existing features: {e}")
                return {}
                
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}")
            return {}
    
    def detect_changed_features(self, features: List[Dict], existing_features: Dict, change_detection_method: str = "content_hash") -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Detect which features need processing based on changes
        
        Args:
            features: Current features from database
            existing_features: Existing features from ChromaDB with metadata
            change_detection_method: Method to detect changes ('content_hash', 'timestamp', 'force_all')
        
        Returns:
            Tuple of (new_features, changed_features, unchanged_features)
        """
        new_features = []
        changed_features = []
        unchanged_features = []
        
        for feature in features:
            feature_id = feature['feature_id']
            
            if change_detection_method == "force_all":
                # Force reprocessing of all features
                if feature_id in existing_features:
                    changed_features.append(feature)
                else:
                    new_features.append(feature)
                continue
            
            if feature_id not in existing_features:
                # This is a new feature
                new_features.append(feature)
                continue
            
            existing_feature = existing_features[feature_id]
            
            if change_detection_method == "content_hash":
                # Compare content hash
                current_hash = self.calculate_content_hash(feature)
                existing_hash = existing_feature.get('content_hash', '')
                
                if current_hash != existing_hash:
                    logger.debug(f"Feature {feature_id} content changed (hash: {existing_hash} -> {current_hash})")
                    changed_features.append(feature)
                else:
                    unchanged_features.append(feature)
                    
            elif change_detection_method == "timestamp":
                # Compare timestamps (if available)
                feature_updated = feature.get('updated_at', feature.get('created_at'))
                existing_updated = existing_feature.get('last_updated', '')
                
                if feature_updated and feature_updated > existing_updated:
                    logger.debug(f"Feature {feature_id} timestamp updated ({existing_updated} -> {feature_updated})")
                    changed_features.append(feature)
                else:
                    unchanged_features.append(feature)
            else:
                # Default to content hash method
                current_hash = self.calculate_content_hash(feature)
                existing_hash = existing_feature.get('content_hash', '')
                
                if current_hash != existing_hash:
                    changed_features.append(feature)
                else:
                    unchanged_features.append(feature)
        
        return new_features, changed_features, unchanged_features

    def get_existing_feature_ids(self):
        """Get list of feature IDs already in ChromaDB (backward compatibility)"""
        existing_features = self.get_existing_features_with_metadata()
        return set(existing_features.keys())
    
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
    
    def generate_all_feature_embeddings(self, limit=None, game_id=None, save_progress_every=10, dimensions=None, resume=True, change_detection="content_hash"):
        """
        Generate embeddings for all features with enhanced change detection
        
        Args:
            limit: Limit number of features to process
            game_id: Filter by specific game ID
            save_progress_every: Progress update frequency
            dimensions: Custom embedding dimensions
            resume: Enable resume functionality
            change_detection: Method for detecting changes ('content_hash', 'timestamp', 'force_all', 'skip_existing')
        """
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
                    "change_detection_method": change_detection,
                    "field_token_stats": {
                        "name": {"total": 0, "count": 0, "avg": 0.0},
                        "description": {"total": 0, "count": 0, "avg": 0.0}
                    }
                },
                "features": []
            }
        
        original_count = len(features)
        
        # Enhanced resume functionality with change detection
        features_to_process = []
        skipped_count = 0
        new_count = 0
        changed_count = 0
        unchanged_count = 0
        
        if resume:
            logger.info(f"🔍 Analyzing features for changes using method: {change_detection}")
            existing_features = self.get_existing_features_with_metadata()
            
            if existing_features:
                new_features, changed_features, unchanged_features = self.detect_changed_features(
                    features, existing_features, change_detection
                )
                
                new_count = len(new_features)
                changed_count = len(changed_features)
                unchanged_count = len(unchanged_features)
                
                if change_detection == "skip_existing":
                    # Traditional resume - skip all existing features
                    features_to_process = new_features
                    skipped_count = changed_count + unchanged_count
                    logger.info(f"🔄 Traditional resume: Processing {new_count} new features, skipping {skipped_count} existing")
                else:
                    # Enhanced resume - process new and changed features
                    features_to_process = new_features + changed_features
                    skipped_count = unchanged_count
                    
                    logger.info(f"🔄 Enhanced resume analysis:")
                    logger.info(f"   📊 New features: {new_count}")
                    logger.info(f"   🔄 Changed features: {changed_count}")
                    logger.info(f"   ✅ Unchanged features (skipped): {unchanged_count}")
                    logger.info(f"   📈 Total to process: {len(features_to_process)}")
                    
                    if changed_count > 0:
                        logger.info(f"   🔍 Change detection method: {change_detection}")
                        # Log some examples of changed features
                        for i, feature in enumerate(changed_features[:3]):  # Show first 3 examples
                            logger.info(f"      • Feature {feature['feature_id']}: {feature.get('name', 'Unnamed')[:40]}...")
                        if changed_count > 3:
                            logger.info(f"      • ... and {changed_count - 3} more")
            else:
                logger.info("🆕 No existing features found - processing all features")
                features_to_process = features
                new_count = len(features)
        else:
            logger.info("⚠️  Resume disabled - processing all features (ignoring existing)")
            features_to_process = features
            new_count = len(features)

        if len(features_to_process) == 0:
            logger.info("✅ No features need processing - all are up to date!")
            return {
                "metadata": {
                    "total_features_in_db": original_count,
                    "new_features": new_count,
                    "changed_features": changed_count,
                    "unchanged_features": unchanged_count,
                    "skipped_features": skipped_count,
                    "features_processed": 0,
                    "model": "text-embedding-3-large",
                    "dimensions": dimensions,
                    "change_detection_method": change_detection,
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

        embeddings_data = {
            "metadata": {
                "total_features_in_db": original_count,
                "new_features": new_count,
                "changed_features": changed_count,
                "unchanged_features": unchanged_count,
                "skipped_features": skipped_count,
                "features_processed": len(features_to_process),
                "model": "text-embedding-3-large",
                "dimensions": dimensions,
                "change_detection_method": change_detection,
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
        
        logger.info(f"🚀 Starting embedding generation for {len(features_to_process)} features")
        if dimensions:
            logger.info(f"🎯 Using custom dimensions: {dimensions}")
        
        for i, feature in enumerate(features_to_process, 1):
            logger.info(f"Processing feature {i}/{len(features_to_process)} (ID: {feature['feature_id']}): {feature.get('name', 'Unnamed')[:50]}...")
            
            combined_text = self.combine_feature_text(feature)
            field_tokens = self.calculate_field_tokens(feature)
            content_hash = self.calculate_content_hash(feature)
            
            if not combined_text.strip():
                logger.warning(f"Feature {feature['feature_id']} has no text content, skipping embedding generation")
                feature_data = {
                    **feature,
                    "combined_text": combined_text,
                    "content_hash": content_hash,
                    "embedding": [],
                    "embedding_dimension": 0,
                    "success": False,
                    "error": "No text content to embed",
                    "token_breakdown": field_tokens,
                    "actual_tokens": 0,
                    "dimensions": dimensions,
                    "embedding_generated_at": datetime.now().isoformat()
                }
                embeddings_data["metadata"]["failed_embeddings"] += 1
            else:
                embedding_result = self.generate_embedding_for_text(combined_text, dimensions=dimensions)
                
                feature_data = {
                    **feature,
                    "combined_text": combined_text,
                    "content_hash": content_hash,
                    "embedding": embedding_result["embedding"],
                    "embedding_dimension": len(embedding_result["embedding"]) if embedding_result["embedding"] else 0,
                    "success": embedding_result["success"],
                    "model": embedding_result.get("model", ""),
                    "dimensions": embedding_result.get("dimensions"),
                    "attempts": embedding_result.get("attempts", 1),
                    "token_breakdown": field_tokens,
                    "embedding_generated_at": datetime.now().isoformat()
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
            if i % save_progress_every == 0 or i == len(features_to_process):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(features_to_process) - i) / rate if rate > 0 else 0
                
                logger.info(f"Progress: {i}/{len(features_to_process)} ({(i/len(features_to_process)*100):.1f}%) | "
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
            embeddings_data["metadata"]["successful_embeddings"] / len(features_to_process) * 100
        ) if len(features_to_process) > 0 else 0.0
        
        logger.info(f"🎉 Embedding generation completed!")
        logger.info(f"  📊 Total in database: {original_count}")
        logger.info(f"  🆕 New features: {new_count}")
        logger.info(f"  🔄 Changed features: {changed_count}")
        logger.info(f"  ✅ Unchanged (skipped): {unchanged_count}")
        logger.info(f"  🚀 Processed: {len(features_to_process)}")
        logger.info(f"  ✓ Successful: {embeddings_data['metadata']['successful_embeddings']}")
        logger.info(f"  ✗ Failed: {embeddings_data['metadata']['failed_embeddings']}")
        logger.info(f"  📈 Success rate: {embeddings_data['metadata']['success_rate']:.1f}%")
        logger.info(f"  🎯 Total tokens: {embeddings_data['metadata']['total_tokens']}")
        logger.info(f"  📊 Avg tokens per embedding: {embeddings_data['metadata']['avg_tokens_per_embedding']}")
        logger.info(f"  ⏱️  Processing time: {embeddings_data['metadata']['processing_time_seconds']:.1f} seconds")
        
        # Log field statistics
        field_stats = embeddings_data["metadata"]["field_token_stats"]
        logger.info(f"  📝 Field Token Statistics:")
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
            logger.info(f"  📁 File size: {file_size / (1024*1024):.1f} MB")
            
            # Print detailed summary
            metadata = embeddings_data['metadata']
            logger.info(f"\n=== FINAL SUMMARY ===")
            logger.info(f"🤖 Model: {metadata['model']}")
            logger.info(f"🎯 Dimensions: {metadata.get('dimensions', 'default (3072)')}")
            logger.info(f"🔍 Change detection: {metadata.get('change_detection_method', 'content_hash')}")
            logger.info(f"📊 Total features in database: {metadata['total_features_in_db']}")
            logger.info(f"🆕 New features: {metadata.get('new_features', 0)}")
            logger.info(f"🔄 Changed features: {metadata.get('changed_features', 0)}")
            logger.info(f"⏭️  Unchanged (skipped): {metadata.get('unchanged_features', 0)}")
            logger.info(f"🚀 Features processed: {metadata.get('features_processed', 0)}")
            logger.info(f"✅ Successful embeddings: {metadata.get('successful_embeddings', 0)}")
            logger.info(f"❌ Failed embeddings: {metadata.get('failed_embeddings', 0)}")
            logger.info(f"📈 Success rate: {metadata.get('success_rate', 0):.1f}%")
            logger.info(f"🎯 Total tokens used: {metadata['total_tokens']}")
            logger.info(f"📊 Average tokens per embedding: {metadata.get('avg_tokens_per_embedding', 0)}")
            logger.info(f"⏱️  Processing time: {metadata.get('processing_time_seconds', 0):.1f} seconds")
            
            # Cost estimation (approximate)
            estimated_cost = metadata['total_tokens'] * 0.00013 / 1000  # $0.00013 per 1K tokens for text-embedding-3-large
            logger.info(f"💰 Estimated API cost: ${estimated_cost:.4f}")
            
            # Field-level statistics
            field_stats = metadata.get('field_token_stats', {})
            if any(stats['count'] > 0 for stats in field_stats.values()):
                logger.info(f"\n--- Field Token Statistics ---")
                for field, stats in field_stats.items():
                    if stats['count'] > 0:
                        logger.info(f"📝 {field.capitalize()}: {stats['total']} total tokens, {stats['count']} fields, {stats['avg']} avg tokens/field")
            
            if metadata.get('failed_embeddings', 0) > 0:
                logger.warning(f"⚠️  {metadata['failed_embeddings']} features failed to generate embeddings")
                logger.warning("   Check the logs above for specific error details")
            
        except Exception as e:
            logger.error(f"✗ Failed to save embeddings: {str(e)}")
            raise 