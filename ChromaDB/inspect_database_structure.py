#!/usr/bin/env python3
"""
Inspect ChromaDB structure and demonstrate correlation with SQL database
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.chromadb_manager import ChromaDBManager
from ChromaDB.vector_search_interface import GameDataSearchInterface
from ChromaDB.database_connection import DatabaseConnection

def inspect_chromadb_structure():
    """Inspect the ChromaDB structure and show how IDs correlate to SQL"""
    
    print("=== ChromaDB Structure Analysis ===\n")
    
    # Initialize ChromaDB
    chroma_manager = ChromaDBManager()
    
    try:
        # Get collection info
        features_collection = chroma_manager.client.get_collection("game_features")
        screenshots_collection = chroma_manager.client.get_collection("game_screenshots")
        
        print("📊 Collections Summary:")
        print(f"  Features: {features_collection.count()} items")
        print(f"  Screenshots: {screenshots_collection.count()} items")
        
        # Sample a few feature records to show structure
        print("\n🎯 Sample Feature Records:")
        feature_sample = features_collection.get(limit=3)
        
        for i, (doc_id, metadata, document) in enumerate(zip(
            feature_sample['ids'], 
            feature_sample['metadatas'], 
            feature_sample['documents']
        )):
            print(f"\n  Record {i+1}:")
            print(f"    ChromaDB ID: {doc_id}")
            print(f"    SQL Feature ID: {metadata.get('feature_id')}")
            print(f"    Game ID: {metadata.get('game_id')}")
            print(f"    Name: {metadata.get('name')}")
            print(f"    Type: {metadata.get('type')}")
            print(f"    Token Count: {metadata.get('token_count')}")
            print(f"    Document Text: {document[:100]}...")
        
        # Sample a few screenshot records
        print("\n📸 Sample Screenshot Records:")
        screenshot_sample = screenshots_collection.get(limit=3)
        
        for i, (doc_id, metadata, document) in enumerate(zip(
            screenshot_sample['ids'], 
            screenshot_sample['metadatas'], 
            screenshot_sample['documents']
        )):
            print(f"\n  Record {i+1}:")
            print(f"    ChromaDB ID: {doc_id}")
            print(f"    SQL Screenshot ID: {metadata.get('screenshot_id')}")
            print(f"    Game ID: {metadata.get('game_id')}")
            print(f"    Path: {metadata.get('path')}")
            print(f"    Caption: {metadata.get('caption')}")
            print(f"    Type: {metadata.get('type')}")
            print(f"    Token Count: {metadata.get('token_count')}")
            print(f"    Document Text: {document[:100]}...")
            
    except Exception as e:
        print(f"❌ Error accessing collections: {e}")
        return

def demonstrate_search_correlation():
    """Demonstrate how search results correlate back to SQL database"""
    
    print("\n\n=== Search Results Correlation Demo ===\n")
    
    # Initialize search interface
    search_interface = GameDataSearchInterface()
    
    # Perform a sample search
    query = "building construction"
    print(f"🔍 Searching for: '{query}'\n")
    
    # Search features
    feature_results = search_interface.search_game_features(query, limit=3)
    
    print("📋 Feature Search Results with SQL Correlation:")
    for i, result in enumerate(feature_results, 1):
        print(f"\n  Result {i}:")
        print(f"    Distance: {result['distance']:.4f}")
        print(f"    SQL Feature ID: {result.get('name')} (from metadata)")
        print(f"    Game ID: {result['game_id']}")
        print(f"    Name: {result['name']}")
        print(f"    Description: {result['description'][:100]}...")
        print(f"    Content: {result['content'][:100]}...")
        
        # Show how to extract SQL ID for correlation
        # The feature_id is stored in the metadata and can be used for SQL queries
        print(f"    → Use this for SQL: SELECT * FROM features_game WHERE feature_id = {result.get('feature_id', 'N/A')}")

def demonstrate_sql_correlation():
    """Show how to use search results to query SQL database"""
    
    print("\n\n=== SQL Database Correlation Example ===\n")
    
    try:
        # Initialize database connection
        db = DatabaseConnection()
        search_interface = GameDataSearchInterface()
        
        # Perform vector search
        query = "farming agriculture"
        results = search_interface.search_game_features(query, limit=2)
        
        print(f"🔍 Vector search for: '{query}'")
        print(f"Found {len(results)} results\n")
        
        # For each result, show SQL correlation
        conn = db.get_connection()
        cursor = conn.cursor()
        
        for i, result in enumerate(results, 1):
            print(f"Result {i} - Distance: {result['distance']:.4f}")
            print(f"  Vector result name: {result['name']}")
            
            # Extract feature_id from metadata (this requires checking how it's stored)
            # Let's check what fields are available
            print(f"  Available fields: {list(result.keys())}")
            
            # Note: We need to extract the feature_id from the ChromaDB metadata
            # This would typically be done by parsing the result metadata
            
        cursor.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

def show_id_mapping_structure():
    """Show the exact ID mapping between ChromaDB and SQL"""
    
    print("\n\n=== ID Mapping Structure ===\n")
    
    print("📋 ChromaDB ID Format:")
    print("  Features: 'feature_{sql_feature_id}'")
    print("    Example: 'feature_123' → SQL feature_id = 123")
    print("")
    print("  Screenshots: 'screenshot_{sql_screenshot_id}'")
    print("    Example: 'screenshot_456' → SQL screenshot_id = 456")
    print("")
    
    print("🔗 Metadata Structure:")
    print("  Features contain:")
    print("    - type: 'feature'")
    print("    - feature_id: str(sql_feature_id)")
    print("    - name: feature name")
    print("    - description: feature description") 
    print("    - game_id: associated game")
    print("    - token_count: embedding token count")
    print("    - created_at: timestamp")
    print("")
    print("  Screenshots contain:")
    print("    - type: 'screenshot'")
    print("    - screenshot_id: str(sql_screenshot_id)")
    print("    - path: image file path")
    print("    - caption: screenshot caption")
    print("    - game_id: associated game")
    print("    - token_count: embedding token count")
    print("    - capture_time: when screenshot was taken")
    print("    - created_at: timestamp")

def extract_sql_ids_from_results(search_results):
    """Helper function to extract SQL IDs from ChromaDB search results"""
    
    sql_ids = []
    
    for result in search_results:
        if result.get('type') == 'feature':
            # Extract feature_id from metadata
            feature_id = result.get('feature_id')  # This should be in metadata
            if feature_id:
                sql_ids.append(('feature', int(feature_id)))
                
        elif result.get('type') == 'screenshot':
            # Extract screenshot_id from metadata
            screenshot_id = result.get('screenshot_id')  # This should be in metadata
            if screenshot_id:
                sql_ids.append(('screenshot', int(screenshot_id)))
    
    return sql_ids

def main():
    """Main function to run all demonstrations"""
    
    try:
        inspect_chromadb_structure()
        show_id_mapping_structure()
        demonstrate_search_correlation()
        demonstrate_sql_correlation()
        
        print("\n\n🎯 Key Takeaways:")
        print("1. ChromaDB stores original SQL IDs in metadata")
        print("2. Use metadata['feature_id'] or metadata['screenshot_id'] for SQL correlation")
        print("3. ChromaDB IDs are prefixed: 'feature_123', 'screenshot_456'")
        print("4. All original data fields are preserved in metadata")
        print("5. Vector search returns metadata allowing easy SQL correlation")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 