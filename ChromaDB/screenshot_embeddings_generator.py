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

class ScreenshotEmbeddingsGenerator:
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
        
    def query_screenshots_from_database(self, limit=None, game_id=None):
        """Query screenshots from PostgreSQL database with optional timestamps for change detection"""
        logger.info(f"Querying screenshots from database (limit: {limit}, game_id: {game_id})")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Check if timestamp columns exist in the table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'screenshots' 
            AND column_name IN ('created_at', 'updated_at', 'last_updated')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        has_created_at = 'created_at' in existing_columns
        has_updated_at = 'updated_at' in existing_columns
        has_last_updated = 'last_updated' in existing_columns
        
        # Build query based on available columns
        base_fields = "screenshot_id, path, game_id, caption, elements, description, capture_time"
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
                FROM screenshots 
                WHERE game_id = %s
                ORDER BY capture_time DESC
            """
            params = (game_id,)
        else:
            query = f"""
                SELECT {fields}
                FROM screenshots 
                ORDER BY capture_time DESC
            """
            params = ()
            
        if limit:
            query += " LIMIT %s"
            params = params + (limit,)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        screenshots = []
        for row in results:
            # Unpack based on available columns
            screenshot_id = row[0]
            path = row[1] 
            game_id = row[2]
            caption = row[3]
            elements = row[4]
            description = row[5]
            capture_time = row[6]
            
            screenshot_data = {
                "screenshot_id": str(screenshot_id),
                "path": path or "",
                "game_id": str(game_id) if game_id else "",
                "caption": caption or "",
                "elements": elements,
                "description": description or "",
                "capture_time": capture_time.isoformat() if capture_time else ""
            }
            
            # Add timestamp fields if available
            col_index = 7
            if has_created_at:
                created_at = row[col_index] if len(row) > col_index else None
                screenshot_data["created_at"] = created_at.isoformat() if created_at else None
                col_index += 1
            
            if has_updated_at:
                updated_at = row[col_index] if len(row) > col_index else None
                screenshot_data["updated_at"] = updated_at.isoformat() if updated_at else None
                col_index += 1
            elif has_last_updated:
                last_updated = row[col_index] if len(row) > col_index else None
                # Map last_updated to updated_at for consistency in the rest of the code
                screenshot_data["updated_at"] = last_updated.isoformat() if last_updated else None
                screenshot_data["last_updated"] = last_updated.isoformat() if last_updated else None
                col_index += 1
            
            # If no timestamps available, use None (content hash method will still work)
            if not has_created_at:
                screenshot_data["created_at"] = None
            if not has_updated_at and not has_last_updated:
                screenshot_data["updated_at"] = None
                
            screenshots.append(screenshot_data)
        
        logger.info(f"Retrieved {len(screenshots)} screenshots from database")
        return screenshots
    
    def format_elements_to_text(self, elements_json):
        """Convert JSONB elements to readable text"""
        if not elements_json:
            return ""
            
        try:
            if isinstance(elements_json, (dict, list)):
                elements = elements_json
            else:
                elements = json.loads(elements_json) if isinstance(elements_json, str) else elements_json
            
            if isinstance(elements, list):
                formatted_elements = []
                for element in elements:
                    if isinstance(element, dict):
                        parts = []
                        if element.get('name'):
                            parts.append(f"Element: {element['name']}")
                        if element.get('type'):
                            parts.append(f"Type: {element['type']}")
                        if element.get('description'):
                            parts.append(f"Description: {element['description']}")
                        if parts:
                            formatted_elements.append(" - ".join(parts))
                return "; ".join(formatted_elements)
            elif isinstance(elements, dict):
                parts = []
                if elements.get('name'):
                    parts.append(f"Element: {elements['name']}")
                if elements.get('type'):
                    parts.append(f"Type: {elements['type']}")
                if elements.get('description'):
                    parts.append(f"Description: {elements['description']}")
                return " - ".join(parts)
            else:
                return str(elements)
                
        except (json.JSONDecodeError, TypeError):
            return str(elements_json) if elements_json else ""
    
    def combine_screenshot_text(self, screenshot):
        """Combine caption, description, and elements for embedding"""
        text_parts = []
        
        if screenshot.get("caption"):
            text_parts.append(f"Caption: {screenshot['caption']}")
            
        if screenshot.get("description"):
            text_parts.append(f"Description: {screenshot['description']}")
            
        if screenshot.get("elements"):
            elements_text = self.format_elements_to_text(screenshot["elements"])
            if elements_text:
                text_parts.append(f"UI Elements: {elements_text}")
        
        return " | ".join(text_parts)
    
    def calculate_content_hash(self, screenshot):
        """Calculate hash of screenshot content for change detection"""
        # Combine the fields that affect embeddings for hashing
        content_parts = [
            screenshot.get("caption", ""),
            screenshot.get("description", ""),
            str(screenshot.get("elements", ""))  # Convert elements to string for hashing
        ]
        content_string = "|".join(content_parts)
        return hashlib.sha256(content_string.encode('utf-8')).hexdigest()[:16]  # First 16 chars for brevity
    
    def calculate_field_tokens(self, screenshot):
        """Calculate estimated tokens for each field separately"""
        tokens = {
            "caption": 0,
            "description": 0,
            "elements": 0
        }
        
        # Rough estimation: ~4 characters per token
        if screenshot.get("caption"):
            tokens["caption"] = max(1, len(screenshot["caption"]) // 4)
            
        if screenshot.get("description"):
            tokens["description"] = max(1, len(screenshot["description"]) // 4)
            
        # For elements, get the formatted text length
        elements_text = self.format_elements_to_text(screenshot.get("elements"))
        if elements_text:
            tokens["elements"] = max(1, len(elements_text) // 4)
            
        return tokens
    
    def get_existing_screenshots_with_metadata(self):
        """Get existing screenshots from ChromaDB with their content hashes and metadata"""
        try:
            from .chromadb_manager import ChromaDBManager
            chroma_manager = ChromaDBManager()
            
            # Try to get the collection, create it if it doesn't exist
            try:
                collection = chroma_manager.client.get_collection("game_screenshots")
            except Exception:
                # Collection doesn't exist yet, no existing screenshots
                logger.info("ChromaDB collection 'game_screenshots' doesn't exist yet - starting fresh")
                return {}
            
            # Get all existing documents with metadata
            try:
                results = collection.get(include=['metadatas'])
                existing_screenshots = {}
                
                if results and 'ids' in results and 'metadatas' in results:
                    for doc_id, metadata in zip(results['ids'], results['metadatas']):
                        # Extract screenshot_id from "screenshot_123" format
                        if doc_id.startswith('screenshot_'):
                            try:
                                screenshot_id = doc_id.replace('screenshot_', '')  # Keep as string for screenshots
                                existing_screenshots[screenshot_id] = {
                                    'id': doc_id,
                                    'content_hash': metadata.get('content_hash', ''),
                                    'last_updated': metadata.get('last_updated', ''),
                                    'path': metadata.get('path', ''),
                                    'caption': metadata.get('caption', ''),
                                    'description': metadata.get('description', ''),
                                    'embedding_generated_at': metadata.get('embedding_generated_at', '')
                                }
                            except ValueError:
                                continue
                
                logger.info(f"Found {len(existing_screenshots)} existing screenshots in ChromaDB with metadata")
                return existing_screenshots
                
            except Exception as e:
                logger.warning(f"Could not retrieve existing screenshots: {e}")
                return {}
                
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}")
            return {}
    
    def detect_changed_screenshots(self, screenshots: List[Dict], existing_screenshots: Dict, change_detection_method: str = "content_hash") -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Detect which screenshots need processing based on changes
        
        Args:
            screenshots: Current screenshots from database
            existing_screenshots: Existing screenshots from ChromaDB with metadata
            change_detection_method: Method to detect changes ('content_hash', 'timestamp', 'force_all')
        
        Returns:
            Tuple of (new_screenshots, changed_screenshots, unchanged_screenshots)
        """
        new_screenshots = []
        changed_screenshots = []
        unchanged_screenshots = []
        
        for screenshot in screenshots:
            screenshot_id = screenshot['screenshot_id']
            
            if change_detection_method == "force_all":
                # Force reprocessing of all screenshots
                if screenshot_id in existing_screenshots:
                    changed_screenshots.append(screenshot)
                else:
                    new_screenshots.append(screenshot)
                continue
            
            if screenshot_id not in existing_screenshots:
                # This is a new screenshot
                new_screenshots.append(screenshot)
                continue
            
            existing_screenshot = existing_screenshots[screenshot_id]
            
            if change_detection_method == "content_hash":
                # Compare content hash
                current_hash = self.calculate_content_hash(screenshot)
                existing_hash = existing_screenshot.get('content_hash', '')
                
                if current_hash != existing_hash:
                    logger.debug(f"Screenshot {screenshot_id} content changed (hash: {existing_hash} -> {current_hash})")
                    changed_screenshots.append(screenshot)
                else:
                    unchanged_screenshots.append(screenshot)
                    
            elif change_detection_method == "timestamp":
                # Compare timestamps (if available)
                screenshot_updated = screenshot.get('updated_at', screenshot.get('created_at', screenshot.get('capture_time')))
                existing_updated = existing_screenshot.get('last_updated', '')
                
                if screenshot_updated and screenshot_updated > existing_updated:
                    logger.debug(f"Screenshot {screenshot_id} timestamp updated ({existing_updated} -> {screenshot_updated})")
                    changed_screenshots.append(screenshot)
                else:
                    unchanged_screenshots.append(screenshot)
            else:
                # Default to content hash method
                current_hash = self.calculate_content_hash(screenshot)
                existing_hash = existing_screenshot.get('content_hash', '')
                
                if current_hash != existing_hash:
                    changed_screenshots.append(screenshot)
                else:
                    unchanged_screenshots.append(screenshot)
        
        return new_screenshots, changed_screenshots, unchanged_screenshots

    def get_existing_screenshot_ids(self):
        """Get list of screenshot IDs already in ChromaDB (backward compatibility)"""
        existing_screenshots = self.get_existing_screenshots_with_metadata()
        return set(existing_screenshots.keys())
    
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

    def generate_all_screenshot_embeddings(self, limit=None, game_id=None, save_progress_every=10, dimensions=None, resume=True, change_detection="content_hash"):
        """
        Generate embeddings for all screenshots with enhanced change detection
        
        Args:
            limit: Limit number of screenshots to process
            game_id: Filter by specific game ID
            save_progress_every: Progress update frequency
            dimensions: Custom embedding dimensions
            resume: Enable resume functionality
            change_detection: Method for detecting changes ('content_hash', 'timestamp', 'force_all', 'skip_existing')
        """
        # Validate dimensions if specified
        if dimensions and (dimensions < 1024 or dimensions > 3072):
            raise ValueError("Dimensions must be between 1024 and 3072 for text-embedding-3-large")
        
        screenshots = self.query_screenshots_from_database(limit, game_id)
        
        if not screenshots:
            logger.warning("No screenshots found in database")
            return {
                "metadata": {
                    "total_screenshots": 0,
                    "model": "text-embedding-3-large",
                    "dimensions": dimensions,
                    "generated_at": datetime.now().isoformat(),
                    "successful_embeddings": 0,
                    "failed_embeddings": 0,
                    "total_tokens": 0,
                    "avg_tokens_per_embedding": 0.0,
                    "change_detection_method": change_detection,
                    "field_token_stats": {
                        "caption": {"total": 0, "count": 0, "avg": 0.0},
                        "description": {"total": 0, "count": 0, "avg": 0.0},
                        "elements": {"total": 0, "count": 0, "avg": 0.0}
                    }
                },
                "screenshots": []
            }
        
        original_count = len(screenshots)
        
        # Enhanced resume functionality with change detection
        screenshots_to_process = []
        skipped_count = 0
        new_count = 0
        changed_count = 0
        unchanged_count = 0
        
        if resume:
            logger.info(f"🔍 Analyzing screenshots for changes using method: {change_detection}")
            existing_screenshots = self.get_existing_screenshots_with_metadata()
            
            if existing_screenshots:
                new_screenshots, changed_screenshots, unchanged_screenshots = self.detect_changed_screenshots(
                    screenshots, existing_screenshots, change_detection
                )
                
                new_count = len(new_screenshots)
                changed_count = len(changed_screenshots)
                unchanged_count = len(unchanged_screenshots)
                
                if change_detection == "skip_existing":
                    # Traditional resume - skip all existing screenshots
                    screenshots_to_process = new_screenshots
                    skipped_count = changed_count + unchanged_count
                    logger.info(f"🔄 Traditional resume: Processing {new_count} new screenshots, skipping {skipped_count} existing")
                else:
                    # Enhanced resume - process new and changed screenshots
                    screenshots_to_process = new_screenshots + changed_screenshots
                    skipped_count = unchanged_count
                    
                    logger.info(f"🔄 Enhanced resume analysis:")
                    logger.info(f"   📊 New screenshots: {new_count}")
                    logger.info(f"   🔄 Changed screenshots: {changed_count}")
                    logger.info(f"   ✅ Unchanged screenshots (skipped): {unchanged_count}")
                    logger.info(f"   📈 Total to process: {len(screenshots_to_process)}")
                    
                    if changed_count > 0:
                        logger.info(f"   🔍 Change detection method: {change_detection}")
                        # Log some examples of changed screenshots
                        for i, screenshot in enumerate(changed_screenshots[:3]):  # Show first 3 examples
                            logger.info(f"      • Screenshot {screenshot['screenshot_id']}: {screenshot.get('path', 'Unknown')[:40]}...")
                        if changed_count > 3:
                            logger.info(f"      • ... and {changed_count - 3} more")
            else:
                logger.info("🆕 No existing screenshots found - processing all screenshots")
                screenshots_to_process = screenshots
                new_count = len(screenshots)
        else:
            logger.info("⚠️  Resume disabled - processing all screenshots (ignoring existing)")
            screenshots_to_process = screenshots
            new_count = len(screenshots)

        if len(screenshots_to_process) == 0:
            logger.info("✅ No screenshots need processing - all are up to date!")
            return {
                "metadata": {
                    "total_screenshots_in_db": original_count,
                    "new_screenshots": new_count,
                    "changed_screenshots": changed_count,
                    "unchanged_screenshots": unchanged_count,
                    "skipped_screenshots": skipped_count,
                    "screenshots_processed": 0,
                    "model": "text-embedding-3-large",
                    "dimensions": dimensions,
                    "change_detection_method": change_detection,
                    "generated_at": datetime.now().isoformat(),
                    "successful_embeddings": 0,
                    "failed_embeddings": 0,
                    "total_tokens": 0,
                    "avg_tokens_per_embedding": 0.0,
                    "field_token_stats": {
                        "caption": {"total": 0, "count": 0, "avg": 0.0},
                        "description": {"total": 0, "count": 0, "avg": 0.0},
                        "elements": {"total": 0, "count": 0, "avg": 0.0}
                    }
                },
                "screenshots": []
            }

        embeddings_data = {
            "metadata": {
                "total_screenshots_in_db": original_count,
                "new_screenshots": new_count,
                "changed_screenshots": changed_count,
                "unchanged_screenshots": unchanged_count,
                "skipped_screenshots": skipped_count,
                "screenshots_processed": len(screenshots_to_process),
                "model": "text-embedding-3-large",
                "dimensions": dimensions,
                "change_detection_method": change_detection,
                "generated_at": datetime.now().isoformat(),
                "successful_embeddings": 0,
                "failed_embeddings": 0,
                "total_tokens": 0,
                "avg_tokens_per_embedding": 0.0,
                "field_token_stats": {
                    "caption": {"total": 0, "count": 0, "avg": 0.0},
                    "description": {"total": 0, "count": 0, "avg": 0.0},
                    "elements": {"total": 0, "count": 0, "avg": 0.0}
                }
            },
            "screenshots": []
        }
        
        start_time = time.time()
        
        logger.info(f"🚀 Starting embedding generation for {len(screenshots_to_process)} screenshots")
        if dimensions:
            logger.info(f"🎯 Using custom dimensions: {dimensions}")
        
        for i, screenshot in enumerate(screenshots_to_process, 1):
            screenshot_path = screenshot.get('path', 'Unknown')
            logger.info(f"Processing screenshot {i}/{len(screenshots_to_process)} (ID: {screenshot['screenshot_id']}): {screenshot_path}")
            
            combined_text = self.combine_screenshot_text(screenshot)
            field_tokens = self.calculate_field_tokens(screenshot)
            content_hash = self.calculate_content_hash(screenshot)
            
            if not combined_text.strip():
                logger.warning(f"Screenshot {screenshot['screenshot_id']} has no text content, skipping embedding generation")
                screenshot_data = {
                    **screenshot,
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
                
                screenshot_data = {
                    **screenshot,
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
                        screenshot_data["actual_tokens"] = actual_tokens
                        screenshot_data["usage"] = embedding_result["usage"]
                    else:
                        # Fallback to estimation
                        estimated_tokens = len(combined_text) // 4
                        embeddings_data["metadata"]["total_tokens"] += estimated_tokens
                        screenshot_data["actual_tokens"] = estimated_tokens
                    
                    # Update field-level statistics
                    for field, token_count in field_tokens.items():
                        if token_count > 0:
                            embeddings_data["metadata"]["field_token_stats"][field]["total"] += token_count
                            embeddings_data["metadata"]["field_token_stats"][field]["count"] += 1
                    
                    logger.debug(f"✓ Screenshot {screenshot['screenshot_id']} embedded successfully ({screenshot_data.get('actual_tokens', 0)} tokens)")
                else:
                    embeddings_data["metadata"]["failed_embeddings"] += 1
                    screenshot_data["error"] = embedding_result["error"]
                    screenshot_data["actual_tokens"] = 0
                    logger.error(f"✗ Screenshot {screenshot['screenshot_id']} embedding failed: {embedding_result['error']}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
            
            embeddings_data["screenshots"].append(screenshot_data)
            
            # Progress update every N screenshots
            if i % save_progress_every == 0 or i == len(screenshots_to_process):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(screenshots_to_process) - i) / rate if rate > 0 else 0
                
                logger.info(f"Progress: {i}/{len(screenshots_to_process)} ({(i/len(screenshots_to_process)*100):.1f}%) | "
                          f"Success: {embeddings_data['metadata']['successful_embeddings']} | "
                          f"Failed: {embeddings_data['metadata']['failed_embeddings']} | "
                          f"Rate: {rate:.1f} screenshots/sec | ETA: {eta:.0f}s")
        
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
            embeddings_data["metadata"]["successful_embeddings"] / len(screenshots_to_process) * 100
        ) if len(screenshots_to_process) > 0 else 0.0
        
        logger.info(f"🎉 Embedding generation completed!")
        logger.info(f"  📊 Total in database: {original_count}")
        logger.info(f"  🆕 New screenshots: {new_count}")
        logger.info(f"  🔄 Changed screenshots: {changed_count}")
        logger.info(f"  ✅ Unchanged (skipped): {unchanged_count}")
        logger.info(f"  🚀 Processed: {len(screenshots_to_process)}")
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
            logger.info(f"📊 Total screenshots in database: {metadata['total_screenshots_in_db']}")
            logger.info(f"🆕 New screenshots: {metadata.get('new_screenshots', 0)}")
            logger.info(f"🔄 Changed screenshots: {metadata.get('changed_screenshots', 0)}")
            logger.info(f"⏭️  Unchanged (skipped): {metadata.get('unchanged_screenshots', 0)}")
            logger.info(f"🚀 Screenshots processed: {metadata.get('screenshots_processed', 0)}")
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
                logger.warning(f"⚠️  {metadata['failed_embeddings']} screenshots failed to generate embeddings")
                logger.warning("   Check the logs above for specific error details")
            
        except Exception as e:
            logger.error(f"✗ Failed to save embeddings: {str(e)}")
            raise 