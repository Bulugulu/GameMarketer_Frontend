"""
Railway-specific ChromaDB connection test
Run this directly on Railway to test ChromaDB connectivity
"""
import os
import sys

print("🚂 Railway ChromaDB Connection Test")
print("=" * 50)

# Check Railway environment
railway_vars = ["RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_DEPLOYMENT_ID"]
print("🔍 Railway Environment Check:")
for var in railway_vars:
    value = os.environ.get(var)
    print(f"   {var}: {'✅' if value else '❌'}")

# Check ChromaDB variables
print("\n🎯 ChromaDB Variables:")
chroma_private = os.environ.get("CHROMA_PRIVATE_URL")
chroma_public = os.environ.get("CHROMA_PUBLIC_URL") 
chroma_token = os.environ.get("CHROMA_SERVER_AUTHN_CREDENTIALS")

print(f"   CHROMA_PRIVATE_URL: {'✅' if chroma_private else '❌'} {chroma_private}")
print(f"   CHROMA_PUBLIC_URL: {'✅' if chroma_public else '❌'} {chroma_public}")
print(f"   CHROMA_SERVER_AUTHN_CREDENTIALS: {'✅' if chroma_token else '❌'} {'***' if chroma_token else 'None'}")

if not chroma_private and not chroma_public:
    print("❌ No ChromaDB URLs found. Make sure ChromaDB service is deployed.")
    sys.exit(1)

# Test both URLs
test_urls = []
if chroma_private:
    test_urls.append(("Private", chroma_private))
if chroma_public:
    test_urls.append(("Public", chroma_public))

print(f"\n🧪 Testing ChromaDB Connections:")

for url_type, url in test_urls:
    print(f"\n📡 Testing {url_type} URL: {url}")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Test 1: With authentication
        if chroma_token:
            print("   🔐 Method 1: With Authentication")
            try:
                client = chromadb.HttpClient(
                    host=url,
                    settings=Settings(
                        chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                        chroma_client_auth_credentials=chroma_token
                        # Note: chroma_client_auth_token_transport_header not supported in 0.6.3
                    )
                )
                
                # Test heartbeat
                heartbeat = client.heartbeat()
                print(f"   ✅ Heartbeat: {heartbeat}")
                
                # Test collections
                collections = client.list_collections()
                print(f"   ✅ Collections: {len(collections)} found")
                for col in collections:
                    print(f"      - {col.name}")
                
                print(f"   ✅ {url_type} URL with auth: SUCCESS!")
                break  # If this works, we're done
                
            except Exception as e:
                print(f"   ❌ With auth failed: {type(e).__name__}: {e}")
        
        # Test 2: Without authentication
        print("   🔓 Method 2: Without Authentication")
        try:
            client = chromadb.HttpClient(host=url)
            
            heartbeat = client.heartbeat()
            print(f"   ✅ Heartbeat: {heartbeat}")
            
            collections = client.list_collections()
            print(f"   ✅ Collections: {len(collections)} found")
            
            print(f"   ✅ {url_type} URL without auth: SUCCESS!")
            break  # If this works, we're done
            
        except Exception as e:
            print(f"   ❌ Without auth failed: {type(e).__name__}: {e}")
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")

# Test basic HTTP connectivity
print(f"\n🌐 Testing Basic HTTP Connectivity:")
for url_type, url in test_urls:
    print(f"\n📍 Testing basic HTTP to {url_type}: {url}")
    try:
        import urllib.request
        import urllib.error
        
        # Try to fetch the root endpoint
        request = urllib.request.Request(url)
        if chroma_token:
            request.add_header("Authorization", f"Bearer {chroma_token}")
        
        response = urllib.request.urlopen(request, timeout=10)
        print(f"   ✅ HTTP response: {response.getcode()}")
        
    except urllib.error.HTTPError as e:
        print(f"   📄 HTTP {e.code}: {e.reason} (this might be normal)")
    except urllib.error.URLError as e:
        print(f"   ❌ URL error: {e}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")

# Test DNS resolution
print(f"\n🔎 Testing DNS Resolution:")
import urllib.parse

for url_type, url in test_urls:
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    
    if hostname:
        print(f"\n📡 Resolving {url_type} hostname: {hostname}")
        try:
            import socket
            ip = socket.gethostbyname(hostname)
            print(f"   ✅ Resolved to: {ip}")
        except Exception as e:
            print(f"   ❌ DNS resolution failed: {e}")

print(f"\n" + "=" * 50)
print("🏁 Railway ChromaDB Test Complete!")

# Instructions
print(f"\n💡 Next Steps:")
print("1. If all tests fail, ChromaDB service might not be running")
print("2. If DNS fails, check service names in Railway dashboard") 
print("3. If HTTP works but ChromaDB fails, check ChromaDB version compatibility")
print("4. Try restarting the ChromaDB service in Railway") 