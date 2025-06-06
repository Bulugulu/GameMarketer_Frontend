#!/usr/bin/env python3
"""
Export features from local ChromaDB using the correct connection method
"""

import os
import json
import chromadb
from datetime import datetime

def export_local_features_correct():
    """Export features from local ChromaDB using the working connection method"""
    print("📤 Exporting Features from Local ChromaDB (Correct Method)")
    print("=" * 55)
    
    try:
        # Use the connection method that actually works
        client = chromadb.PersistentClient(path="chroma_db")
        
        # Get features collection
        features_collection = client.get_collection("game_features")
        feature_count = features_collection.count()
        
        print(f"📊 Found {feature_count} features in local database")
        
        if feature_count == 0:
            print("❌ No features found in local database!")
            return False
        
        # Get all features
        print("📥 Retrieving all features...")
        all_features = features_collection.get(
            include=["embeddings", "documents", "metadatas"]
        )
        
        print(f"✅ Retrieved {len(all_features['ids'])} features")
        
        # Convert to the expected JSON format
        features_data = []
        
        print("🔄 Converting to JSON format...")
        for i, (feature_id, embedding, document, metadata) in enumerate(zip(
            all_features['ids'],
            all_features['embeddings'],
            all_features['documents'],
            all_features['metadatas']
        )):
            
            # Extract feature_id from the ID (remove 'feature_' prefix)
            actual_feature_id = feature_id.replace('feature_', '') if feature_id.startswith('feature_') else feature_id
            
            feature_data = {
                "feature_id": actual_feature_id,
                "success": True,
                "embedding": embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                "combined_text": document,
                "name": metadata.get('name', ''),
                "description": metadata.get('description', ''),
                "game_id": metadata.get('game_id', ''),
                "actual_tokens": metadata.get('token_count', len(document.split()) if document else 0),
                "content_hash": metadata.get('content_hash', ''),
                "embedding_generated_at": metadata.get('embedding_generated_at', ''),
                "created_at": metadata.get('created_at', ''),
                "updated_at": metadata.get('last_updated', metadata.get('updated_at', '')),
                "model": metadata.get('model', 'text-embedding-3-large')
            }
            
            features_data.append(feature_data)
            
            if (i + 1) % 20 == 0:
                print(f"   Processed {i + 1}/{feature_count} features...")
        
        # Create the full JSON structure
        total_tokens = sum(f.get('actual_tokens', 0) for f in features_data)
        avg_tokens = total_tokens / len(features_data) if features_data else 0.0
        
        export_data = {
            "metadata": {
                "total_features_in_db": feature_count,
                "new_features": feature_count,
                "changed_features": 0,
                "unchanged_features": 0,
                "skipped_features": 0,
                "features_processed": feature_count,
                "model": "text-embedding-3-large",
                "dimensions": len(features_data[0]['embedding']) if features_data else 0,
                "change_detection_method": "export_from_local_chromadb",
                "generated_at": datetime.now().isoformat(),
                "successful_embeddings": feature_count,
                "failed_embeddings": 0,
                "total_tokens": total_tokens,
                "avg_tokens_per_embedding": avg_tokens,
                "exported_from": "local_chromadb_persistent_client",
                "export_date": datetime.now().isoformat()
            },
            "features": features_data
        }
        
        # Write to JSON file
        output_file = "feature_embeddings.json"
        print(f"💾 Writing to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        file_size = os.path.getsize(output_file) / 1024 / 1024
        print(f"✅ Successfully exported {feature_count} features to {output_file}")
        print(f"📊 File size: {file_size:.1f} MB")
        print(f"📊 Total tokens: {total_tokens:,}")
        print(f"📊 Average tokens per feature: {avg_tokens:.1f}")
        print(f"📊 Embedding dimensions: {len(features_data[0]['embedding']) if features_data else 0}")
        
        # Show sample of what was exported
        print(f"\n👀 Sample exported features:")
        for i, feature in enumerate(features_data[:3]):
            print(f"   {i+1}. {feature['name']} (ID: {feature['feature_id']})")
            print(f"      Tokens: {feature['actual_tokens']}")
            print(f"      Text: {feature['combined_text'][:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = export_local_features_correct()
    
    if success:
        print(f"\n🎉 Export completed successfully!")
        print(f"📋 Next steps:")
        print(f"   1. Run: python railway_upload_and_test.py")
        print(f"   2. This will upload your 96 features to Railway ChromaDB")
        print(f"   3. Your Railway will then have both features AND screenshots!")
    else:
        print(f"\n❌ Export failed. Please check the error messages above.") 