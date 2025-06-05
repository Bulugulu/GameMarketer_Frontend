"""
Test script to diagnose ChromaDB connection issues with Railway
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")

print("🔬 ChromaDB Connection Test")
print("=" * 50)

# Test environment detection
try:
    from utils.config import get_environment, get_chroma_config, is_railway_environment
    
    env = get_environment()
    print(f"\n📍 Environment Detection:")
    print(f"   Detected environment: {env}")
    print(f"   is_railway_environment(): {is_railway_environment()}")
    
    # Show Railway detection variables
    railway_vars = ["RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_DEPLOYMENT_ID", "RAILWAY_ENVIRONMENT_ID"]
    print(f"\n🚂 Railway Variables:")
    for var in railway_vars:
        value = os.environ.get(var)
        print(f"   {var}: {'✅ Present' if value else '❌ Missing'}")
    
    # Show ChromaDB configuration
    chroma_config = get_chroma_config()
    print(f"\n🎯 ChromaDB Configuration:")
    print(f"   is_railway: {chroma_config['is_railway']}")
    print(f"   host: {chroma_config['host']}")
    print(f"   auth_token: {'✅ Present' if chroma_config['auth_token'] else '❌ Missing'}")
    
    # Show Railway ChromaDB variables
    print(f"\n🔗 Railway ChromaDB Variables:")
    chroma_vars = {
        "CHROMA_PRIVATE_URL": os.environ.get("CHROMA_PRIVATE_URL"),
        "CHROMA_PUBLIC_URL": os.environ.get("CHROMA_PUBLIC_URL"),
        "CHROMA_SERVER_AUTHN_CREDENTIALS": os.environ.get("CHROMA_SERVER_AUTHN_CREDENTIALS")
    }
    
    for var, value in chroma_vars.items():
        status = "✅" if value else "❌"
        display = value[:30] + "..." if value and len(value) > 30 else value or "Not set"
        print(f"   {status} {var}: {display}")
    
except ImportError as e:
    print(f"❌ Could not import config: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

# Test ChromaDB connection
print(f"\n🧪 ChromaDB Connection Test:")

if not chroma_config['is_railway']:
    print("⚠️ Not in Railway environment - testing local ChromaDB")
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./ChromaDB/chroma_db")
        print("✅ Local ChromaDB connection successful")
        
        # Test basic operations
        collections = client.list_collections()
        print(f"   Found {len(collections)} collections")
        
    except Exception as e:
        print(f"❌ Local ChromaDB connection failed: {e}")

else:
    print("🚂 Testing Railway ChromaDB connection...")
    
    if not chroma_config['host']:
        print("❌ No ChromaDB host configured - make sure ChromaDB service is deployed")
        sys.exit(1)
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        print(f"   Attempting connection to: {chroma_config['host']}")
        print(f"   Using authentication: {'Yes' if chroma_config['auth_token'] else 'No'}")
        
        # Test Method 1: With authentication (if token available)
        if chroma_config['auth_token']:
            print("\n   📡 Method 1: Token Authentication")
            try:
                client = chromadb.HttpClient(
                    host=chroma_config['host'],
                    settings=Settings(
                        chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                        chroma_client_auth_credentials=chroma_config['auth_token'],
                        chroma_client_auth_token_transport_header="Authorization"
                    )
                )
                
                # Test connection
                print("   Testing heartbeat...")
                heartbeat = client.heartbeat()
                print(f"   ✅ Heartbeat successful: {heartbeat}")
                
                print("   Testing list_collections...")
                collections = client.list_collections()
                print(f"   ✅ Found {len(collections)} collections")
                
                if collections:
                    for col in collections:
                        print(f"      - {col.name}")
                
                print("   ✅ Method 1 (Token Auth) - SUCCESS!")
                
            except Exception as e:
                print(f"   ❌ Method 1 (Token Auth) failed: {e}")
                print(f"   Error type: {type(e).__name__}")
                
                # Test Method 2: Without authentication
                print("\n   📡 Method 2: No Authentication")
                try:
                    client = chromadb.HttpClient(host=chroma_config['host'])
                    
                    heartbeat = client.heartbeat()
                    print(f"   ✅ Heartbeat successful: {heartbeat}")
                    
                    collections = client.list_collections()
                    print(f"   ✅ Found {len(collections)} collections")
                    print("   ✅ Method 2 (No Auth) - SUCCESS!")
                    
                except Exception as e2:
                    print(f"   ❌ Method 2 (No Auth) also failed: {e2}")
                    print(f"   Error type: {type(e2).__name__}")
        else:
            # Only test without auth if no token
            print("\n   📡 Method: No Authentication (no token provided)")
            try:
                client = chromadb.HttpClient(host=chroma_config['host'])
                
                heartbeat = client.heartbeat()
                print(f"   ✅ Heartbeat successful: {heartbeat}")
                
                collections = client.list_collections()
                print(f"   ✅ Found {len(collections)} collections")
                print("   ✅ No Auth method - SUCCESS!")
                
            except Exception as e:
                print(f"   ❌ No Auth method failed: {e}")
                print(f"   Error type: {type(e).__name__}")
    
    except ImportError as e:
        print(f"❌ ChromaDB import failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

# Test different host formats if connection failed
if chroma_config['is_railway'] and chroma_config['host']:
    print(f"\n🔄 Testing Alternative Connection Methods:")
    
    # Parse the URL for different formats
    import urllib.parse
    parsed = urllib.parse.urlparse(chroma_config['host'])
    
    alternatives = [
        chroma_config['host'],  # Original
        f"{parsed.scheme}://{parsed.netloc}",  # Clean URL
        parsed.netloc,  # Just host:port
        parsed.hostname or parsed.netloc.split(':')[0]  # Just hostname
    ]
    
    print(f"   Original host: {chroma_config['host']}")
    print(f"   Parsed URL: {parsed}")
    
    for i, alt_host in enumerate(alternatives):
        if alt_host and alt_host != chroma_config['host']:
            print(f"\n   🔍 Alternative {i+1}: {alt_host}")
            try:
                import chromadb
                client = chromadb.HttpClient(host=alt_host)
                heartbeat = client.heartbeat()
                print(f"   ✅ Alternative {i+1} works! Heartbeat: {heartbeat}")
                break
            except Exception as e:
                print(f"   ❌ Alternative {i+1} failed: {type(e).__name__}: {e}")

print(f"\n" + "=" * 50)
print("🏁 ChromaDB Connection Test Complete!")

# Manual override test
print(f"\n🔧 Manual Override Test:")
print("If you want to force Railway mode locally, set:")
print("   export FORCE_RAILWAY_MODE=true")
print("If you want to force local mode on Railway, set:")
print("   export FORCE_LOCAL_MODE=true") 