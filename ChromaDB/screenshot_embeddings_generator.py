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
        """Query screenshots from PostgreSQL database"""
        logger.info(f"Querying screenshots from database (limit: {limit}, game_id: {game_id})")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if game_id:
            query = """
                SELECT screenshot_id, path, game_id, caption, elements, description, capture_time
                FROM screenshots 
                WHERE game_id = %s
                ORDER BY capture_time DESC
            """
            params = (game_id,)
        else:
            query = """
                SELECT screenshot_id, path, game_id, caption, elements, description, capture_time
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
            screenshot_id, path, game_id, caption, elements, description, capture_time = row
            screenshots.append({
                "screenshot_id": str(screenshot_id),
                "path": path or "",
                "game_id": str(game_id) if game_id else "",
                "caption": caption or "",
                "elements": elements,
                "description": description or "",
                "capture_time": capture_time.isoformat() if capture_time else ""
            })
        
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
    
    def get_existing_screenshot_ids(self):
        """Get list of screenshot IDs already in ChromaDB"""
        try:
            from .chromadb_manager import ChromaDBManager
            chroma_manager = ChromaDBManager()
            
            # Try to get the collection, create it if it doesn't exist
            try:
                collection = chroma_manager.client.get_collection("game_screenshots")
            except Exception:
                # Collection doesn't exist yet, no existing screenshots
                logger.info("ChromaDB collection 'game_screenshots' doesn't exist yet - starting fresh")
                return set()
            
            # Get all existing IDs
            try:
                results = collection.get()
                existing_ids = set()
                
                if results and 'ids' in results:
                    for doc_id in results['ids']:
                        # Extract screenshot_id from "screenshot_123" format
                        if doc_id.startswith('screenshot_'):
                            try:
                                screenshot_id = int(doc_id.replace('screenshot_', ''))
                                existing_ids.add(screenshot_id)
                            except ValueError:
                                continue
                
                logger.info(f"Found {len(existing_ids)} existing screenshots in ChromaDB")
                return existing_ids
                
            except Exception as e:
                logger.warning(f"Could not retrieve existing screenshots: {e}")
                return set()
                
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB: {e}")
            return set()

    def generate_all_screenshot_embeddings(self, limit=None, game_id=None, save_progress_every=10, dimensions=None, resume=True):
        """Generate embeddings for all screenshots with progress tracking, enhanced analytics, and resume capability"""
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
                    "field_token_stats": {
                        "caption": {"total": 0, "count": 0, "avg": 0.0},
                        "description": {"total": 0, "count": 0, "avg": 0.0},
                        "elements": {"total": 0, "count": 0, "avg": 0.0}
                    }
                },
                "screenshots": []
            }
        
        original_count = len(screenshots)
        
        # Resume functionality - skip already processed screenshots
        if resume:
            existing_ids = self.get_existing_screenshot_ids()
            if existing_ids:
                screenshots = [s for s in screenshots if s['screenshot_id'] not in existing_ids]
                skipped_count = original_count - len(screenshots)
                
                if skipped_count > 0:
                    logger.info(f"🔄 Resume mode: Skipping {skipped_count} already processed screenshots")
                    logger.info(f"📊 Processing {len(screenshots)} remaining screenshots ({len(screenshots)}/{original_count})")
                else:
                    logger.info("✅ All screenshots already processed!")
                    if len(screenshots) == 0:
                        # Return early if nothing to process
                        return {
                            "metadata": {
                                "total_screenshots": original_count,
                                "skipped_screenshots": skipped_count,
                                "new_screenshots": 0,
                                "model": "text-embedding-3-large",
                                "dimensions": dimensions,
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
            else:
                logger.info("🆕 No existing screenshots found - processing all screenshots")
                skipped_count = 0
        else:
            logger.info("⚠️  Resume disabled - processing all screenshots (may create duplicates)")
            skipped_count = 0

        embeddings_data = {
            "metadata": {
                "total_screenshots_in_db": original_count,
                "skipped_screenshots": skipped_count,
                "new_screenshots_to_process": len(screenshots),
                "model": "text-embedding-3-large",
                "dimensions": dimensions,
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
        
        logger.info(f"Starting embedding generation for {len(screenshots)} screenshots")
        if dimensions:
            logger.info(f"Using custom dimensions: {dimensions}")
        
        for i, screenshot in enumerate(screenshots, 1):
            screenshot_path = screenshot.get('path', 'Unknown')
            logger.info(f"Processing screenshot {i}/{len(screenshots)} (ID: {screenshot['screenshot_id']}): {screenshot_path}")
            
            combined_text = self.combine_screenshot_text(screenshot)
            field_tokens = self.calculate_field_tokens(screenshot)
            
            if not combined_text.strip():
                logger.warning(f"Screenshot {screenshot['screenshot_id']} has no text content, skipping embedding generation")
                screenshot_data = {
                    **screenshot,
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
                
                screenshot_data = {
                    **screenshot,
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
            if i % save_progress_every == 0 or i == len(screenshots):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (len(screenshots) - i) / rate if rate > 0 else 0
                
                logger.info(f"Progress: {i}/{len(screenshots)} ({(i/len(screenshots)*100):.1f}%) | "
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
            embeddings_data["metadata"]["successful_embeddings"] / len(screenshots) * 100
        )
        
        logger.info(f"Embedding generation completed!")
        logger.info(f"  Total screenshots: {len(screenshots)}")
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
            logger.info(f"Total screenshots processed: {metadata['total_screenshots_in_db']}")
            logger.info(f"Successful embeddings: {metadata['successful_embeddings']}")
            logger.info(f"Failed embeddings: {metadata['failed_embeddings']}")
            logger.info(f"Success rate: {metadata.get('success_rate', 0):.1f}%")
            logger.info(f"Total tokens used: {metadata['total_tokens']}")
            logger.info(f"Average tokens per embedding: {metadata.get('avg_tokens_per_embedding', 0)}")
            
        except Exception as e:
            logger.error(f"✗ Failed to save embeddings: {str(e)}")
            raise 