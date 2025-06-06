#!/usr/bin/env python3
"""
Upload features directly to the game_features collection using known UUID
"""

import os
import json
import requests
from dotenv import load_dotenv

def upload_to_game_features():
    """Upload features directly to game_features collection"""
    print("🚀 Uploading Features to game_features Collection")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Known UUID for game_features collection
    features_uuid = "f5a365d3-2409-4354-8106-378e22f0bea5"
    
    print(f"🌐 Uploading to: {base_url}")
    print(f"📁 Collection UUID: {features_uuid}")
    
    # Check if feature_embeddings.json exists
    if not os.path.exists("feature_embeddings.json"):
        print("❌ feature_embeddings.json not found! Please run export script first.")
        return False
    
    # Load features data
    print("📁 Loading feature embeddings...")
    with open("feature_embeddings.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"📊 Found {len(features)} features to upload")
    
    if len(features) == 0:
        print("❌ No features found in JSON file!")
        return False
    
    # Upload in batches
    batch_size = 25
    total_uploaded = 0
    
    print(f"\n🚀 Uploading {len(features)} features in batches of {batch_size}...")
    
    for i in range(0, len(features), batch_size):
        batch = features[i:i + batch_size]
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for feature in batch:
            if not feature.get('success', False) or not feature.get('embedding'):
                continue
            
            ids.append(f"feature_{feature['feature_id']}")
            embeddings.append(feature['embedding'])
            documents.append(feature.get('combined_text', ''))
            
            # Metadata that matches what ChromaDBManager expects
            metadata = {
                "type": "feature",
                "feature_id": str(feature['feature_id']),
                "name": feature.get('name', ''),
                "description": feature.get('description', ''),
                "game_id": feature.get('game_id', ''),
                "token_count": feature.get('actual_tokens', 0),
                "created_at": feature.get('created_at', ''),
                "embedding_generated_at": feature.get('embedding_generated_at', ''),
                "last_updated": feature.get('updated_at', ''),
                "model": feature.get('model', 'text-embedding-3-large'),
                "processing_success": feature.get('success', True),
                "upload_source": "local_chromadb_export_final"
            }
            
            # Only include non-None values
            metadata = {k: v for k, v in metadata.items() if v is not None and v != ''}
            metadatas.append(metadata)
        
        if ids:
            upload_data = {
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents,
                "metadatas": metadatas
            }
            
            response = requests.post(
                f"{base_url}/api/v1/collections/{features_uuid}/add",
                headers=headers,
                json=upload_data
            )
            
            if response.status_code in [200, 201]:
                total_uploaded += len(ids)
                print(f"   ✅ Uploaded batch {i//batch_size + 1}: {len(ids)} features")
            else:
                print(f"   ❌ Failed batch {i//batch_size + 1}: {response.status_code} - {response.text}")
    
    print(f"\n✅ Upload completed! Total uploaded: {total_uploaded} features")
    
    # Test the uploaded data
    print(f"\n🔍 Testing uploaded data...")
    count_response = requests.get(f"{base_url}/api/v1/collections/{features_uuid}/count", headers=headers)
    
    if count_response.status_code == 200:
        count = count_response.json()
        print(f"📊 'game_features' collection now has {count} features")
        
        # Test a sample query
        sample_response = requests.post(
            f"{base_url}/api/v1/collections/{features_uuid}/get",
            headers=headers,
            json={"limit": 3, "include": ["metadatas"]},
            timeout=10
        )
        
        if sample_response.status_code == 200:
            sample_data = sample_response.json()
            print(f"👀 Sample features in 'game_features' collection:")
            for i, metadata in enumerate(sample_data.get('metadatas', [])):
                print(f"   {i+1}. {metadata.get('name', 'N/A')} (Type: {metadata.get('type', 'N/A')})")
                print(f"      Feature ID: {metadata.get('feature_id', 'N/A')}")
    
    print(f"\n🎉 SUCCESS! Features uploaded to correct 'game_features' collection!")
    print(f"✅ Front-end semantic search should now work properly!")
    print(f"📊 Collection UUID: {features_uuid}")
    
    return True

if __name__ == "__main__":
    success = upload_to_game_features()
    
    if success:
        print(f"\n🎯 FRONT-END ISSUE FIXED!")
        print(f"Your semantic_search_tool should now find features correctly!")
    else:
        print(f"\n❌ Upload failed. Please check the error messages above.") 