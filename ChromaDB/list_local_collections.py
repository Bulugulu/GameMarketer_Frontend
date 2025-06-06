#!/usr/bin/env python3
"""
List all collections in local ChromaDB
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from root directory
load_dotenv('../.env.local')

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.chromadb_manager import ChromaDBManager

def list_local_collections():
    """List all collections in local ChromaDB"""
    print("📋 Listing Local ChromaDB Collections")
    print("=" * 40)
    
    try:
        # Initialize local ChromaDB manager
        chroma_manager = ChromaDBManager()
        
        # List all collections
        collections = chroma_manager.client.list_collections()
        
        print(f"📊 Found {len(collections)} collections in local database:")
        
        for i, collection in enumerate(collections, 1):
            count = collection.count()
            print(f"   {i}. {collection.name} - {count} items")
            
            if count > 0:
                # Get a sample to see what type of data it contains
                try:
                    sample = collection.get(limit=1, include=["metadatas"])
                    if sample.get('metadatas') and len(sample['metadatas']) > 0:
                        metadata = sample['metadatas'][0]
                        data_type = metadata.get('type', 'unknown')
                        print(f"      Type: {data_type}")
                        
                        # Show relevant metadata based on type
                        if data_type == 'feature':
                            print(f"      Feature: {metadata.get('name', 'N/A')}")
                        elif data_type == 'screenshot':
                            print(f"      Screenshot: {metadata.get('path', 'N/A')}")
                        else:
                            print(f"      Sample metadata keys: {list(metadata.keys())}")
                except Exception as e:
                    print(f"      (Could not get sample: {str(e)})")
        
        if len(collections) == 0:
            print("❌ No collections found in local ChromaDB!")
            print("\n💡 This could mean:")
            print("   1. Your features are stored under a different collection name")
            print("   2. Your local ChromaDB is empty")
            print("   3. Your features are in a different ChromaDB instance")
        
        return collections
        
    except Exception as e:
        print(f"❌ Failed to list collections: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    collections = list_local_collections()
    
    if collections:
        print(f"\n✅ Successfully listed {len(collections)} collections")
        print("\n💡 If you see your features here under a different name,")
        print("   we can modify the export script to use the correct collection name.")
    else:
        print("\n❌ No collections found or error occurred") 