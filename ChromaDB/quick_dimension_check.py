#!/usr/bin/env python3
"""
Quick script to check ChromaDB embedding dimensions
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.chromadb_manager import ChromaDBManager

def quick_dimension_check():
    """Simple dimension check without complex logic"""
    print("🔍 Quick Dimension Check")
    print("=" * 30)
    
    try:
        chroma_manager = ChromaDBManager()
        collections = ["game_features", "game_screenshots"]
        
        for collection_name in collections:
            print(f"\n📁 {collection_name}:")
            try:
                collection = chroma_manager.client.get_collection(collection_name)
                count = collection.count()
                print(f"   Items: {count}")
                
                if count > 0:
                    # Simple approach - just get one result
                    sample = collection.get(limit=1, include=['embeddings'])
                    
                    if 'embeddings' in sample and sample['embeddings']:
                        embedding = sample['embeddings'][0]
                        dimensions = len(embedding)
                        print(f"   ✅ Dimensions: {dimensions}")
                    else:
                        print(f"   ❌ No embeddings")
                else:
                    print(f"   ⚠️  Empty collection")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

if __name__ == "__main__":
    quick_dimension_check() 