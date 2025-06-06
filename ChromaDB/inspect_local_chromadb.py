#!/usr/bin/env python3
"""
Inspect the actual local ChromaDB database
"""

import os
import sqlite3
import chromadb
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root directory
load_dotenv('../.env.local')

def inspect_sqlite_directly():
    """Inspect the SQLite database directly"""
    print("🔍 Direct SQLite Database Inspection")
    print("=" * 45)
    
    db_path = "chroma_db/chroma.sqlite3"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    file_size = os.path.getsize(db_path) / 1024 / 1024
    print(f"📊 Database file: {db_path} ({file_size:.1f} MB)")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📋 Tables in database:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} rows")
        
        # Look for collections specifically
        cursor.execute("SELECT * FROM collections LIMIT 10")
        collections = cursor.fetchall()
        
        print(f"\n📁 Collections found:")
        for i, collection in enumerate(collections):
            print(f"   {i+1}. {collection}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ SQLite inspection failed: {str(e)}")

def inspect_chromadb_different_ways():
    """Try different ways to connect to ChromaDB"""
    print("\n🔄 Trying Different ChromaDB Connection Methods")
    print("=" * 50)
    
    # Method 1: Direct path
    print("1️⃣ Method 1: Direct path to chroma_db")
    try:
        client1 = chromadb.PersistentClient(path="chroma_db")
        collections1 = client1.list_collections()
        print(f"   ✅ Found {len(collections1)} collections:")
        for coll in collections1:
            count = coll.count()
            print(f"      - {coll.name}: {count} items")
        return client1, collections1
    except Exception as e:
        print(f"   ❌ Method 1 failed: {str(e)}")
    
    # Method 2: Absolute path
    print("\n2️⃣ Method 2: Absolute path")
    try:
        abs_path = os.path.abspath("chroma_db")
        client2 = chromadb.PersistentClient(path=abs_path)
        collections2 = client2.list_collections()
        print(f"   ✅ Found {len(collections2)} collections:")
        for coll in collections2:
            count = coll.count()
            print(f"      - {coll.name}: {count} items")
        return client2, collections2
    except Exception as e:
        print(f"   ❌ Method 2 failed: {str(e)}")
    
    # Method 3: ChromaDB subfolder
    print("\n3️⃣ Method 3: ChromaDB subfolder")
    try:
        client3 = chromadb.PersistentClient(path="ChromaDB/chroma_db")
        collections3 = client3.list_collections()
        print(f"   ✅ Found {len(collections3)} collections:")
        for coll in collections3:
            count = coll.count()
            print(f"      - {coll.name}: {count} items")
        return client3, collections3
    except Exception as e:
        print(f"   ❌ Method 3 failed: {str(e)}")
    
    # Method 4: Current directory
    print("\n4️⃣ Method 4: Current directory")
    try:
        client4 = chromadb.PersistentClient(path=".")
        collections4 = client4.list_collections()
        print(f"   ✅ Found {len(collections4)} collections:")
        for coll in collections4:
            count = coll.count()
            print(f"      - {coll.name}: {count} items")
        return client4, collections4
    except Exception as e:
        print(f"   ❌ Method 4 failed: {str(e)}")
    
    return None, []

def inspect_collection_details(client, collections):
    """Inspect details of found collections"""
    print(f"\n📋 Detailed Collection Inspection")
    print("=" * 40)
    
    for i, collection in enumerate(collections):
        print(f"\n📁 Collection {i+1}: {collection.name}")
        
        try:
            count = collection.count()
            print(f"   📊 Count: {count} items")
            
            if count > 0:
                # Get sample data
                sample = collection.get(limit=3, include=["metadatas", "documents"])
                
                print(f"   👀 Sample data:")
                for j, (doc_id, metadata, document) in enumerate(zip(
                    sample.get('ids', []),
                    sample.get('metadatas', []),
                    sample.get('documents', [])
                )):
                    print(f"      {j+1}. ID: {doc_id}")
                    print(f"         Type: {metadata.get('type', 'unknown')}")
                    
                    if metadata.get('type') == 'feature':
                        print(f"         Feature: {metadata.get('name', 'N/A')}")
                    elif metadata.get('type') == 'screenshot':
                        print(f"         Screenshot: {metadata.get('path', 'N/A')}")
                    
                    print(f"         Document: {document[:60] if document else 'N/A'}...")
                    
        except Exception as e:
            print(f"   ❌ Error inspecting collection: {str(e)}")

def main():
    """Main inspection function"""
    print("🔍 Local ChromaDB Database Inspection")
    print("=" * 50)
    
    # First, check if the directory exists
    if os.path.exists("chroma_db"):
        print("✅ chroma_db directory found")
        
        # List contents
        contents = os.listdir("chroma_db")
        print(f"📁 Contents: {len(contents)} items")
        for item in contents:
            if os.path.isfile(f"chroma_db/{item}"):
                size = os.path.getsize(f"chroma_db/{item}") / 1024 / 1024
                print(f"   📄 {item} ({size:.1f} MB)")
            else:
                print(f"   📁 {item}/")
    else:
        print("❌ chroma_db directory not found")
        return
    
    # Try SQLite inspection
    inspect_sqlite_directly()
    
    # Try different ChromaDB connection methods
    client, collections = inspect_chromadb_different_ways()
    
    if client and collections:
        inspect_collection_details(client, collections)
        return client, collections
    else:
        print("\n❌ Could not connect to ChromaDB with any method")
        return None, []

if __name__ == "__main__":
    client, collections = main()
    
    if collections:
        print(f"\n🎉 SUCCESS! Found {len(collections)} collections in local ChromaDB!")
        print("Now we can export them to Railway.")
    else:
        print("\n🤔 No collections accessible. The database might need different connection parameters.") 