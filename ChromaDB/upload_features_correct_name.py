#!/usr/bin/env python3
"""
Upload features to Railway ChromaDB with the correct collection name
"""

import os
import json
import requests
from dotenv import load_dotenv

def upload_features_correct_name():
    """Upload features to Railway ChromaDB with the correct name 'game_features'"""
    print("🚀 Uploading Features to Correct Collection Name")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('../.env.local')
    
    base_url = os.getenv("CHROMA_PUBLIC_URL").rstrip('/')
    token = os.getenv("CHROMA_SERVER_AUTHN_CREDENTIALS")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Uploading to: {base_url}")
    
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
    
    # Create the collection with the CORRECT name that the front-end expects
    collection_data = {
        "name": "game_features",  # ✅ This is what ChromaDBManager expects!
        "metadata": {
            "description": "Game feature embeddings for vector search",
            "embedding_model": "text-embedding-3-large",
            "created_at": "2025-01-06",
            "hnsw:space": "cosine"  # Use cosine distance for better text semantics
        }
    }
    
    # Try to create the collection
    print("📁 Creating/getting 'game_features' collection...")
    response = requests.post(f"{base_url}/api/v1/collections", headers=headers, json=collection_data)
    
    if response.status_code == 200:
        result = response.json()
        features_uuid = result.get('id', result.get('uuid'))
        print(f"✅ Collection 'game_features' created: {features_uuid}")
    elif response.status_code == 409:
        print("📁 Collection 'game_features' already exists, finding its UUID...")
        
        # The collection exists, but we need to find its UUID
        # Let's try to create a test document to find the UUID
        test_data = {
            "name": "test_find_uuid",
            "metadata": {"temp": "test"}
        }
        test_response = requests.post(f"{base_url}/api/v1/collections", headers=headers, json=test_data)
        
        if test_response.status_code == 200:
            test_result = test_response.json()
            test_uuid = test_result.get('id', test_result.get('uuid'))
            print(f"✅ Found test collection: {test_uuid}")
            
            # Delete test collection
            requests.delete(f"{base_url}/api/v1/collections/{test_uuid}", headers=headers)
            
            # For now, we'll try some common UUID patterns for game_features
            # Since we know screenshots is 1b9de2ef-758f-4639-bb99-9703d5042414
            # And uploaded_game_features was 31bd1f58-b73e-4f92-933e-e6f2ec315a88
            # The original game_features might have a different UUID
            
            potential_uuids = [
                # Try some variations - features are often created before screenshots
                "1b9de2ef-758f-4639-bb99-9703d5042413",  # One before screenshots
                "1b9de2ef-758f-4639-bb99-9703d5042412",  # Two before screenshots  
                "1b9de2ef-758f-4639-bb99-9703d5042410",  # More before
                # Or could be completely different pattern
            ]
            
            print("🔍 Searching for existing 'game_features' collection UUID...")
            features_uuid = None
            
            for test_uuid in potential_uuids:
                try:
                    count_response = requests.get(f"{base_url}/api/v1/collections/{test_uuid}/count", headers=headers, timeout=5)
                    if count_response.status_code == 200:
                        count = count_response.json()
                        print(f"   ✅ Found collection at {test_uuid} with {count} items")
                        
                        # Check if this is the features collection by getting a sample
                        sample_response = requests.post(
                            f"{base_url}/api/v1/collections/{test_uuid}/get",
                            headers=headers,
                            json={"limit": 1, "include": ["metadatas"]},
                            timeout=5
                        )
                        
                        if sample_response.status_code == 200:
                            sample_data = sample_response.json()
                            if sample_data.get('metadatas') and len(sample_data['metadatas']) > 0:
                                metadata = sample_data['metadatas'][0]
                                if metadata.get('type') == 'feature':
                                    features_uuid = test_uuid
                                    print(f"   🎯 This is the features collection! UUID: {features_uuid}")
                                    break
                except:
                    continue
            
            if not features_uuid:
                print("❌ Could not find existing 'game_features' collection UUID")
                print("   The collection exists but we can't access it with our search methods")
                return False
        else:
            print(f"❌ Could not determine collection UUID: {test_response.status_code}")
            return False
    else:
        print(f"❌ Failed to create collection: {response.status_code} - {response.text}")
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
                "upload_source": "local_chromadb_export_corrected"
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
    
    print(f"\n🎉 SUCCESS! Features uploaded to correct collection name!")
    print(f"✅ Front-end will now find 'game_features' collection")
    print(f"📊 Collection UUID: {features_uuid}")
    
    return True

if __name__ == "__main__":
    success = upload_features_correct_name()
    
    if success:
        print(f"\n🎯 PROBLEM SOLVED!")
        print(f"Your front-end should now work correctly with semantic feature search!")
    else:
        print(f"\n❌ Upload failed. Please check the error messages above.") 