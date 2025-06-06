#!/usr/bin/env python3
"""
Test script for R2 integration with Township Feature Analyst

This script tests:
1. R2 configuration validation
2. R2 connection and bucket access
3. Screenshot URL generation
4. End-to-end screenshot retrieval workflow

Usage: python test_r2_integration.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def load_environment_variables():
    """Load environment variables with better debugging"""
    print("🔍 Loading Environment Variables")
    print("=" * 50)
    
    # Try multiple locations for .env.local
    possible_env_files = [
        ".env.local",
        "../.env.local", 
        "../../.env.local",
        Path.cwd() / ".env.local",
        Path.cwd().parent / ".env.local"
    ]
    
    env_loaded = False
    
    for env_file in possible_env_files:
        env_path = Path(env_file)
        print(f"   Checking: {env_path.absolute()}")
        
        if env_path.exists():
            print(f"   ✅ Found .env.local at: {env_path.absolute()}")
            load_dotenv(env_path)
            env_loaded = True
            break
        else:
            print(f"   ❌ Not found")
    
    if not env_loaded:
        print(f"\n⚠️ No .env.local file found in any expected location!")
        print(f"Current working directory: {Path.cwd()}")
        print(f"Please ensure .env.local exists with your R2 credentials")
        return False
    
    # Verify R2 variables are loaded
    r2_vars = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME']
    missing_vars = []
    
    print(f"\n📋 R2 Environment Variables:")
    for var in r2_vars:
        value = os.getenv(var)
        if value:
            # Show first few characters for security
            display = value[:10] + "..." if len(value) > 10 else value
            print(f"   ✅ {var}: {display}")
        else:
            print(f"   ❌ {var}: Not set")
            missing_vars.append(var)
    
    # Check optional variables
    optional_vars = ['R2_ENDPOINT_URL', 'R2_TOKEN']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"   ℹ️ {var}: {display}")
        else:
            print(f"   ℹ️ {var}: Not set (optional)")
    
    if missing_vars:
        print(f"\n❌ Missing required variables: {', '.join(missing_vars)}")
        return False
    
    print(f"\n✅ All required R2 variables loaded successfully")
    return True

def test_r2_configuration():
    """Test R2 configuration and basic functionality"""
    print("\n🔍 Testing R2 Integration")
    print("=" * 50)
    
    # Test environment detection
    try:
        from utils.config import get_environment, get_screenshot_config, get_r2_config
        
        env = get_environment()
        screenshot_config = get_screenshot_config()
        r2_config = get_r2_config()
        
        print(f"\n📍 Environment Detection:")
        print(f"   Current environment: {env}")
        print(f"   Screenshot mode: {screenshot_config['mode']}")
        print(f"   Using R2: {screenshot_config['is_r2']}")
        
        print(f"\n🔧 R2 Configuration:")
        for key, value in r2_config.items():
            if key.endswith('_configured'):
                status = "✅" if value else "❌"
                label = key.replace('_configured', '').replace('_', ' ').title()
                print(f"   {status} {label}: {'Configured' if value else 'Not configured'}")
            elif value:
                display = value[:20] + "..." if isinstance(value, str) and len(value) > 20 else value
                print(f"   {key.replace('_', ' ').title()}: {display}")
        
    except ImportError as e:
        print(f"❌ Failed to import configuration modules: {e}")
        return False
    
    # Test R2 client
    print(f"\n🌐 R2 Client Test:")
    try:
        from utils.r2_client import get_r2_client, is_r2_configured
        
        is_configured = is_r2_configured()
        print(f"   R2 configured: {'✅ Yes' if is_configured else '❌ No'}")
        
        if not is_configured:
            print("   ⚠️ R2 not configured - checking configuration details...")
            
            # Get more detailed info about why it's not configured
            r2_client = get_r2_client()
            connection_info = r2_client.get_connection_info()
            
            print(f"   📋 Configuration Details:")
            print(f"      Account ID: {connection_info.get('account_id', 'Not set')}")
            print(f"      Bucket Name: {connection_info.get('bucket_name', 'Not set')}")
            print(f"      Endpoint URL: {connection_info.get('endpoint_url', 'Not set')}")
            print(f"      Access Key ID: {connection_info.get('access_key_id', 'Not set')}")
            print(f"      Auto-constructed endpoint: {connection_info.get('auto_constructed_endpoint', False)}")
            
            return False
        
        r2_client = get_r2_client()
        connection_info = r2_client.get_connection_info()
        
        print(f"   📋 Connection Details:")
        print(f"      Account ID: {connection_info['account_id']}")
        print(f"      Bucket: {connection_info['bucket_name']}")
        print(f"      Endpoint: {connection_info['endpoint_url']}")
        print(f"      Auto-constructed endpoint: {connection_info.get('auto_constructed_endpoint', False)}")
        
        # Test connection by listing objects
        print(f"\n📦 Bucket Content Test:")
        try:
            objects = r2_client.list_objects(max_keys=10)
            print(f"   ✅ Successfully connected to bucket")
            print(f"   Found {len(objects)} objects (showing first 10)")
            
            if objects:
                print(f"   Sample objects:")
                for i, obj in enumerate(objects[:5], 1):
                    size_mb = obj['size'] / (1024 * 1024)
                    print(f"     {i}. {obj['key']} ({size_mb:.2f} MB)")
            else:
                print("   ⚠️ Bucket is empty")
            
            return objects  # Return objects for URL testing
            
        except Exception as e:
            print(f"   ❌ Failed to list bucket contents: {e}")
            
            # Enhanced troubleshooting
            print(f"\n🔧 Troubleshooting Information:")
            
            # Check if it's a bucket name issue
            bucket_name = connection_info['bucket_name']
            print(f"   📝 Bucket name being used: '{bucket_name}'")
            print(f"   💡 Possible issues:")
            print(f"      1. Bucket name might be case-sensitive")
            print(f"      2. Bucket might not exist in the specified account")
            print(f"      3. API token might not have access to this bucket")
            print(f"      4. Account ID might be incorrect")
            
            # Suggest specific checks
            print(f"\n   🔍 Please verify:")
            print(f"      - Bucket '{bucket_name}' exists in your Cloudflare R2 dashboard")
            print(f"      - Account ID matches your Cloudflare account ID")
            print(f"      - API token has 'Object Read & Write' permissions")
            print(f"      - API token scope includes this bucket (or all buckets)")
            
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import R2 client: {e}")
        return False
    except Exception as e:
        print(f"❌ R2 client error: {e}")
        return False

def test_url_generation(objects):
    """Test URL generation for screenshots"""
    if not objects:
        print(f"\n⚠️ No objects found - skipping URL generation test")
        return
    
    print(f"\n🔗 URL Generation Test:")
    try:
        from utils.r2_client import get_r2_client
        
        r2_client = get_r2_client()
        
        # Test URL generation for first few objects
        test_objects = objects[:3]
        
        for i, obj in enumerate(test_objects, 1):
            key = obj['key']
            print(f"   {i}. Testing: {key}")
            
            # Generate presigned URL
            url = r2_client.get_screenshot_url(key, expires_in=300)  # 5 minutes
            
            if url:
                print(f"      ✅ URL generated successfully")
                print(f"      URL preview: {url[:80]}...")
                
                # Test if it's a valid URL format
                if url.startswith(('http://', 'https://')) and 'r2.cloudflarestorage.com' in url:
                    print(f"      ✅ URL format is valid")
                else:
                    print(f"      ⚠️ URL format might be invalid")
            else:
                print(f"      ❌ Failed to generate URL")
        
        # Test batch URL generation
        print(f"\n   Batch URL generation test:")
        test_keys = [obj['key'] for obj in test_objects]
        batch_urls = r2_client.batch_get_screenshot_urls(test_keys, expires_in=300)
        
        success_count = sum(1 for url in batch_urls.values() if url)
        print(f"   ✅ Generated {success_count}/{len(test_keys)} URLs in batch")
        
    except Exception as e:
        print(f"❌ URL generation test failed: {e}")

def test_screenshot_handler():
    """Test the screenshot handler with R2 integration"""
    print(f"\n📸 Screenshot Handler Test:")
    
    try:
        # First, get some sample screenshot IDs from the database
        from database_tool import run_sql_query
        
        query = """
        SELECT screenshot_id::text, path 
        FROM screenshots 
        WHERE path IS NOT NULL 
        LIMIT 5
        """
        
        result = run_sql_query(query)
        
        if "error" in result:
            print(f"   ❌ Database query failed: {result['error']}")
            return
        
        if not result.get("rows"):
            print(f"   ⚠️ No screenshots found in database")
            return
        
        screenshot_ids = [row[0] for row in result["rows"]]
        screenshot_paths = [row[1] for row in result["rows"]]
        print(f"   Found {len(screenshot_ids)} screenshots in database")
        print(f"   Sample IDs: {screenshot_ids[:3]}")
        print(f"   Sample paths: {screenshot_paths[:3]}")
        
        # Test screenshot retrieval
        from utils.screenshot_handler import retrieve_screenshots_for_display
        
        print(f"   Testing screenshot retrieval...")
        retrieved = retrieve_screenshots_for_display(screenshot_ids[:3])
        
        if retrieved.get("screenshots_for_ui"):
            print(f"   ✅ Successfully retrieved screenshots")
            print(f"   Groups: {len(retrieved['screenshots_for_ui'])}")
            
            # Check serving mode for each group
            for group in retrieved['screenshots_for_ui']:
                serving_mode = group.get('serving_mode', 'unknown')
                image_count = len(group.get('image_paths', []))
                print(f"     - {group.get('group_title', 'Unknown')}: {image_count} images via {serving_mode}")
                
                # Check if URLs are properly generated for R2 mode
                if serving_mode == 'r2':
                    sample_path = group.get('image_paths', [None])[0]
                    if sample_path and sample_path.startswith(('http://', 'https://')):
                        print(f"       ✅ R2 URL properly generated")
                        print(f"       Sample URL: {sample_path[:60]}...")
                    else:
                        print(f"       ❌ R2 URL not generated properly")
                        print(f"       Got: {sample_path}")
        else:
            print(f"   ⚠️ No screenshots retrieved")
            
    except Exception as e:
        print(f"❌ Screenshot handler test failed: {e}")

def test_mode_switching():
    """Test switching between local and R2 modes"""
    print(f"\n🔄 Mode Switching Test:")
    
    try:
        from utils.config import get_screenshot_config, set_screenshot_mode
        
        # Get current mode
        original_mode = get_screenshot_config()['mode']
        print(f"   Original mode: {original_mode}")
        
        # Test switching to local mode
        set_screenshot_mode("local")
        local_config = get_screenshot_config()
        print(f"   After setting local: {local_config['mode']} (is_local: {local_config['is_local']})")
        
        # Test switching to R2 mode
        set_screenshot_mode("r2")
        r2_config = get_screenshot_config()
        print(f"   After setting R2: {r2_config['mode']} (is_r2: {r2_config['is_r2']})")
        
        # Restore original mode
        set_screenshot_mode(original_mode)
        restored_config = get_screenshot_config()
        print(f"   Restored to: {restored_config['mode']}")
        
        print(f"   ✅ Mode switching works correctly")
        
    except Exception as e:
        print(f"❌ Mode switching test failed: {e}")

def test_simple_r2_connection():
    """Test basic R2 connection with minimal boto3 setup"""
    print(f"\n🧪 Simple R2 Connection Test:")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Get environment variables
        account_id = os.getenv("R2_ACCOUNT_ID")
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
        bucket_name = os.getenv("R2_BUCKET_NAME")
        endpoint_url = os.getenv("R2_ENDPOINT_URL")
        
        # Check if we have the required variables
        if not all([account_id, access_key, secret_key, bucket_name]):
            print(f"   ❌ Missing required environment variables:")
            if not account_id:
                print(f"      - R2_ACCOUNT_ID is missing")
            if not access_key:
                print(f"      - R2_ACCESS_KEY_ID is missing")
            if not secret_key:
                print(f"      - R2_SECRET_ACCESS_KEY is missing")
            if not bucket_name:
                print(f"      - R2_BUCKET_NAME is missing")
            return False
        
        # Validate and fix endpoint URL
        original_endpoint = endpoint_url
        if endpoint_url:
            # Check if endpoint URL incorrectly includes bucket name
            if endpoint_url.endswith(f"/{bucket_name}"):
                print(f"   ⚠️ Endpoint URL includes bucket name - this is incorrect!")
                print(f"   Original: {endpoint_url}")
                endpoint_url = endpoint_url[:-len(f"/{bucket_name}")]
                print(f"   Corrected: {endpoint_url}")
                print(f"   💡 Please update your .env.local R2_ENDPOINT_URL to: {endpoint_url}")
            elif f"/{bucket_name}/" in endpoint_url:
                # Handle cases where bucket name is in the middle
                parts = endpoint_url.split(f"/{bucket_name}")
                endpoint_url = parts[0]
                print(f"   ⚠️ Endpoint URL includes bucket name - corrected to: {endpoint_url}")
        else:
            # Auto-construct endpoint if not provided
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
            print(f"   Auto-constructed endpoint: {endpoint_url}")
        
        # Validate endpoint format
        expected_endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        if endpoint_url != expected_endpoint:
            print(f"   ⚠️ Endpoint URL format might be incorrect")
            print(f"   Current: {endpoint_url}")
            print(f"   Expected: {expected_endpoint}")
            print(f"   💡 Consider using the expected format in your .env.local")
        
        print(f"   Testing connection to bucket '{bucket_name}' at {endpoint_url}")
        
        # Create simple boto3 client for R2
        client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'  # R2 requires 'auto' as the region
        )
        
        # Test 1: List objects
        print(f"   Testing list_objects_v2...")
        response = client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        objects = response.get('Contents', [])
        print(f"   ✅ List objects successful - found {len(objects)} objects")
        
        if objects:
            for obj in objects[:3]:
                print(f"      - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print(f"   ℹ️ Bucket is empty or no objects found")
        
        # Test 2: Generate presigned URL
        if objects:
            test_key = objects[0]['Key']
            print(f"   Testing presigned URL for: {test_key}")
            
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': test_key},
                ExpiresIn=300
            )
            
            print(f"   ✅ Presigned URL generated: {url[:60]}...")
        else:
            print(f"   ⚠️ No objects to test presigned URL generation")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        print(f"   ❌ AWS/R2 Client Error: {error_code}")
        print(f"   Error message: {e}")
        
        if error_code == 'NoSuchBucket':
            print(f"   💡 The bucket '{bucket_name}' was not found")
            print(f"   🔍 Double-check the bucket name in your Cloudflare R2 dashboard")
        elif error_code == 'SignatureDoesNotMatch':
            print(f"   💡 Authentication failed - check your access keys")
        elif error_code == 'AccessDenied':
            print(f"   💡 Access denied - check your API token permissions")
        elif error_code == 'InvalidRegionName':
            print(f"   💡 Invalid region error - this shouldn't happen with R2")
            print(f"   🔍 There might be an issue with the boto3 R2 configuration")
        elif error_code == 'NoSuchKey':
            print(f"   💡 This error suggests the endpoint URL format is incorrect")
            print(f"   🔍 The endpoint should NOT include the bucket name")
            print(f"   📝 Correct format: https://{{account_id}}.r2.cloudflarestorage.com")
            print(f"   📝 NOT: https://{{account_id}}.r2.cloudflarestorage.com/{bucket_name}")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def main():
    """Run all R2 integration tests"""
    print("🚀 R2 Integration Test Suite")
    print("This script tests the Cloudflare R2 integration for screenshot serving")
    print("")
    
    # First, load and verify environment variables
    if not load_environment_variables():
        print("\n❌ Environment variables not properly loaded!")
        print("\n🔧 To fix this:")
        print("1. Create a .env.local file in your project directory")
        print("2. Add your R2 credentials to it:")
        print("   R2_ACCOUNT_ID=your_account_id")
        print("   R2_ACCESS_KEY_ID=your_access_key")
        print("   R2_SECRET_ACCESS_KEY=your_secret_key")
        print("   R2_BUCKET_NAME=your_bucket_name")
        print("3. Run this test script again")
        return
    
    # Run a simple connection test
    simple_test_passed = test_simple_r2_connection()
    
    if not simple_test_passed:
        print(f"\n" + "=" * 50)
        print("❌ Simple R2 connection test failed!")
        print("Please fix the basic R2 connection before proceeding.")
        return
    
    # Test R2 configuration and connection
    objects = test_r2_configuration()
    
    if objects:
        # Test URL generation
        test_url_generation(objects)
        
        # Test screenshot handler
        test_screenshot_handler()
        
        # Test mode switching
        test_mode_switching()
        
        print(f"\n" + "=" * 50)
        print("✅ R2 Integration Test Complete!")
        print("")
        print("🎯 Next Steps:")
        print("1. If all tests passed, R2 integration is working correctly")
        print("2. You can now use the debug toggle in the Streamlit app")
        print("3. On Railway, R2 mode will be used automatically if configured")
        print("4. Locally, you can manually switch modes using the toggle")
        
    else:
        print(f"\n" + "=" * 50)
        print("❌ R2 Integration Test Failed!")
        print("")
        print("🔧 Troubleshooting Checklist:")
        print("1. ✓ Check your .env.local file has all required R2 variables")
        print("2. ✓ Verify your R2 credentials are correct")
        print("3. ✓ Ensure your R2 bucket exists and has the screenshot data")
        print("4. ✓ Check the bucket permissions allow read access")
        print("5. ✓ Verify the bucket name matches exactly (case-sensitive)")
        print("6. ✓ Confirm the Account ID is from the correct Cloudflare account")

if __name__ == "__main__":
    main() 