#!/usr/bin/env python3
"""
Diagnostic script to inspect ChromaDB collections content
"""
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.chromadb_manager import ChromaDBManager

def diagnose_collections():
    """Diagnose what's actually in ChromaDB collections"""
    print("🔍 ChromaDB Collections Diagnostic")
    print("=" * 40)
    
    try:
        chroma_manager = ChromaDBManager()
        collections = ["game_features", "game_screenshots"]
        
        for collection_name in collections:
            print(f"\n📁 Collection: {collection_name}")
            print("-" * 30)
            
            try:
                collection = chroma_manager.client.get_collection(collection_name)
                count = collection.count()
                print(f"Total items: {count}")
                
                if count > 0:
                    # Get one sample with all available data
                    print("\n🔍 Checking available data types...")
                    
                    # Try different include options
                    include_options = [
                        ['documents'],
                        ['metadatas'], 
                        ['embeddings'],
                        ['documents', 'metadatas'],
                        ['documents', 'metadatas', 'embeddings']
                    ]
                    
                    for includes in include_options:
                        try:
                            sample = collection.get(limit=1, include=includes)
                            print(f"✓ {includes}: Available")
                            
                            # Show what we got
                            for key in includes:
                                if key in sample and sample[key]:
                                    if key == 'embeddings':
                                        if sample[key][0] is not None:
                                            embedding_len = len(sample[key][0]) if hasattr(sample[key][0], '__len__') else 'Unknown'
                                            print(f"   - {key}: Found! Length: {embedding_len}")
                                        else:
                                            print(f"   - {key}: None/Empty")
                                    elif key == 'documents':
                                        doc_preview = str(sample[key][0])[:100] + "..." if len(str(sample[key][0])) > 100 else str(sample[key][0])
                                        print(f"   - {key}: '{doc_preview}'")
                                    elif key == 'metadatas':
                                        if sample[key][0]:
                                            meta_keys = list(sample[key][0].keys())[:5]  # Show first 5 keys
                                            print(f"   - {key}: {meta_keys}")
                                        else:
                                            print(f"   - {key}: Empty")
                                else:
                                    print(f"   - {key}: Missing or empty")
                                    
                        except Exception as e:
                            print(f"✗ {includes}: Error - {e}")
                    
                    # Check IDs
                    try:
                        ids_sample = collection.get(limit=3)
                        if 'ids' in ids_sample and ids_sample['ids']:
                            print(f"\n📋 Sample IDs: {ids_sample['ids']}")
                        else:
                            print(f"\n📋 No IDs found")
                    except Exception as e:
                        print(f"\n📋 Error getting IDs: {e}")
                        
                else:
                    print("⚠️  Collection is empty")
                    
            except Exception as e:
                print(f"❌ Error accessing collection: {e}")
                
        # Additional diagnostic - check if collections need to be recreated
        print(f"\n" + "=" * 40)
        print("💡 Diagnosis:")
        print("If embeddings are missing, you may need to:")
        print("1. Regenerate embeddings: python ChromaDB/setup_vector_database.py --change-detection force_all")
        print("2. Check that embedding generation completed successfully")
        print("3. Verify OpenAI API key is working")
        
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB: {e}")

if __name__ == "__main__":
    diagnose_collections() 