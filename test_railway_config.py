"""
Test script to verify Railway configuration for PostgreSQL and ChromaDB
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

print("🔍 Testing Railway Configuration")
print("=" * 50)

# Test environment detection
from utils.config import get_environment, DB_CONNECTION_PARAMS, get_chroma_config

env = get_environment()
print(f"\n📍 Environment: {env}")
print(f"   Railway detected: {'Yes' if env == 'railway' else 'No'}")

# Test PostgreSQL configuration
print(f"\n🐘 PostgreSQL Configuration:")
print(f"   Host: {DB_CONNECTION_PARAMS['host']}")
print(f"   Database: {DB_CONNECTION_PARAMS['dbname']}")
print(f"   User: {DB_CONNECTION_PARAMS['user']}")
print(f"   Port: {DB_CONNECTION_PARAMS['port']}")
print(f"   Password: {'***' if DB_CONNECTION_PARAMS['password'] else 'Not set'}")

# Test database connection
try:
    import pg8000
    conn = pg8000.connect(**DB_CONNECTION_PARAMS)
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"   ✅ Connection successful!")
    print(f"   PostgreSQL version: {version.split(',')[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"   ❌ Connection failed: {str(e)}")

# Test ChromaDB configuration
print(f"\n🎯 ChromaDB Configuration:")
chroma_config = get_chroma_config()
if chroma_config["is_railway"]:
    print(f"   Mode: Railway (HTTP Client)")
    print(f"   Host: {chroma_config['host']}")
    print(f"   Auth: {'Configured' if chroma_config['auth_token'] else 'Not configured'}")
else:
    print(f"   Mode: Local (File-based)")
    print(f"   Path: ./ChromaDB/chroma_db")

# Test ChromaDB connection
try:
    from ChromaDB.chromadb_manager import ChromaDBManager
    chroma = ChromaDBManager()
    info = chroma.get_database_info()
    print(f"   ✅ Connection successful!")
    print(f"   Database: {info['database_path']}")
    for collection in info['collections']:
        print(f"   Collection '{collection['name']}': {collection['count']} items")
except Exception as e:
    print(f"   ❌ Connection failed: {str(e)}")

# Test OpenAI configuration
print(f"\n🤖 OpenAI Configuration:")
api_key = os.environ.get("OPENAI_API_KEY")
print(f"   API Key: {'✅ Set' if api_key else '❌ Not set'}")

# Test Cohere configuration (optional)
print(f"\n🔄 Cohere Configuration (optional):")
cohere_key = os.environ.get("COHERE_API_KEY")
print(f"   API Key: {'✅ Set' if cohere_key else '⚠️  Not set (reranking disabled)'}")

print("\n" + "=" * 50)
print("✨ Configuration test complete!")

# Summary
issues = []
if not api_key:
    issues.append("OpenAI API key not set")
if env == "railway":
    if not os.environ.get("PGPASSWORD"):
        issues.append("PostgreSQL password not set (add PostgreSQL service in Railway)")
    if chroma_config["host"] and not chroma_config["auth_token"]:
        issues.append("ChromaDB auth token might be needed")

if issues:
    print("\n⚠️  Issues found:")
    for issue in issues:
        print(f"   - {issue}")
else:
    print("\n✅ All configurations look good!") 