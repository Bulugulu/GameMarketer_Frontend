#!/usr/bin/env python3
"""
Export features from local ChromaDB to JSON format for Railway upload
"""

import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from root directory
load_dotenv('../.env.local')

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ChromaDB.chromadb_manager import ChromaDBManager

def export_local_features():
    """Export features from local ChromaDB to JSON file"""
    print("📤 Exporting Features from Local ChromaDB")
    print("=" * 45)
    
    try:
        # Initialize local ChromaDB manager
        chroma_manager = ChromaDBManager()
        
        # Get features collection
        features_collection = chroma_manager.client.get_collection("game_features")
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
        
        # Convert to the expected JSON format
        features_data = []
        
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
                "embedding": embedding,
                "combined_text": document,
                "name": metadata.get('name', ''),
                "description": metadata.get('description', ''),
                "game_id": metadata.get('game_id', ''),
                "actual_tokens": metadata.get('token_count', 0),
                "content_hash": metadata.get('content_hash', ''),
                "embedding_generated_at": metadata.get('embedding_generated_at', ''),
                "created_at": metadata.get('created_at', ''),
                "updated_at": metadata.get('last_updated', ''),
                "model": metadata.get('model', 'text-embedding-3-large')
            }
            
            features_data.append(feature_data)
            
            if (i + 1) % 100 == 0:
                print(f"   Processed {i + 1}/{feature_count} features...")
        
        # Create the full JSON structure
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
                "change_detection_method": "export_from_local",
                "generated_at": datetime.now().isoformat(),
                "successful_embeddings": feature_count,
                "failed_embeddings": 0,
                "total_tokens": sum(f.get('actual_tokens', 0) for f in features_data),
                "avg_tokens_per_embedding": sum(f.get('actual_tokens', 0) for f in features_data) / len(features_data) if features_data else 0.0,
                "exported_from": "local_chromadb",
                "export_date": datetime.now().isoformat()
            },
            "features": features_data
        }
        
        # Write to JSON file
        output_file = "feature_embeddings.json"
        print(f"💾 Writing to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Successfully exported {feature_count} features to {output_file}")
        print(f"📊 File size: {os.path.getsize(output_file) / 1024 / 1024:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = export_local_features()
    
    if success:
        print(f"\n🎉 Export completed!")
        print(f"📋 Next steps:")
        print(f"   1. Run: python railway_upload_and_test.py")
        print(f"   2. This will upload your features to Railway ChromaDB")
    else:
        print(f"\n❌ Export failed. Please check your local ChromaDB.") 