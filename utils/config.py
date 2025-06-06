import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env.local (with error handling)
try:
    load_dotenv(".env.local")
except Exception as e:
    print(f"Warning: Could not parse .env.local file: {e}")
    print("Proceeding with system environment variables only.")

# Initialize OpenAI client
API_KEY = os.environ.get("OPENAI_API_KEY")
CLIENT = None
MODEL_NAME = "gpt-4o"  # Use a model that works well with Agents SDK

# Better Railway environment detection
def is_railway_environment():
    """
    Reliable Railway environment detection using official Railway-provided variables.
    These variables are automatically set by Railway during deployment.
    """
    # Method 1: Check for Railway project ID (always present in Railway runtime)
    if os.environ.get("RAILWAY_PROJECT_ID"):
        return True
    
    # Method 2: Check for Railway service ID (always present in Railway runtime)
    if os.environ.get("RAILWAY_SERVICE_ID"):
        return True
    
    # Method 3: Check for Railway deployment ID (always present in Railway runtime)
    if os.environ.get("RAILWAY_DEPLOYMENT_ID"):
        return True
    
    # Method 4: Check for Railway environment ID (always present in Railway runtime)
    if os.environ.get("RAILWAY_ENVIRONMENT_ID"):
        return True
    
    # Method 5: Manual override for testing Railway mode locally
    if os.environ.get("FORCE_RAILWAY_MODE") == "true":
        return True
    
    # Method 6: Explicit local override (takes precedence)
    if os.environ.get("FORCE_LOCAL_MODE") == "true":
        return False
    
    # Default to local development if no Railway variables detected
    return False

IS_RAILWAY = is_railway_environment()

# Global variable for the database connection parameters
if IS_RAILWAY:
    # Use Railway PostgreSQL environment variables
    DB_CONNECTION_PARAMS = {
        "host": os.environ.get("PGHOST", "postgres.railway.internal"),
        "dbname": os.environ.get("PGDATABASE", "railway"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
        "port": os.environ.get("PGPORT", "5432")
    }
    print(f"🚀 Railway environment detected - using Railway databases")
else:
    # Use local environment variables with underscores (prioritize local naming)
    DB_CONNECTION_PARAMS = {
        "host": os.environ.get("PG_HOST", os.environ.get("DB_HOST", "localhost")),
        "dbname": os.environ.get("PG_DATABASE", os.environ.get("DB_NAME", "township_db")),
        "user": os.environ.get("PG_USER", os.environ.get("DB_USER", "postgres")),
        "password": os.environ.get("PG_PASSWORD", os.environ.get("DATABASE_PASSWORD", os.environ.get("DB_PASSWORD", ""))),
        "port": os.environ.get("PG_PORT", os.environ.get("DB_PORT", "5432"))
    }
    print(f"💻 Local environment detected - using local databases")

# ChromaDB configuration
if IS_RAILWAY:
    # Use Railway ChromaDB environment variables as per their template
    # See: https://railway.com/deploy/kbvIRV
    CHROMA_HOST = os.environ.get("CHROMA_PRIVATE_URL") or os.environ.get("CHROMA_PUBLIC_URL")
    CHROMA_AUTH_TOKEN = os.environ.get("CHROMA_SERVER_AUTHN_CREDENTIALS", "")
    
    print(f"[DEBUG] Railway ChromaDB config:")
    print(f"[DEBUG] - CHROMA_PRIVATE_URL: {'✓' if os.environ.get('CHROMA_PRIVATE_URL') else '✗'}")
    print(f"[DEBUG] - CHROMA_PUBLIC_URL: {'✓' if os.environ.get('CHROMA_PUBLIC_URL') else '✗'}")
    print(f"[DEBUG] - CHROMA_SERVER_AUTHN_CREDENTIALS: {'✓' if CHROMA_AUTH_TOKEN else '✗'}")
    print(f"[DEBUG] - Using host: {CHROMA_HOST}")
else:
    # Use local ChromaDB (file-based) regardless of what Railway variables might be present
    CHROMA_HOST = None  # Will use local file-based ChromaDB
    CHROMA_AUTH_TOKEN = None

# Screenshot serving configuration
def get_screenshot_mode():
    """
    Determine screenshot serving mode based on environment and configuration.
    Returns 'r2' for R2 storage, 'local' for local filesystem.
    """
    # Check for manual override first
    forced_mode = os.environ.get("SCREENSHOT_MODE")
    if forced_mode in ["r2", "local"]:
        return forced_mode
    
    # Auto-detect based on environment
    if IS_RAILWAY:
        # Check if R2 is configured
        r2_vars = ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME", "R2_ENDPOINT_URL"]
        if all(os.environ.get(var) for var in r2_vars):
            return "r2"
        else:
            print("⚠️ Railway environment detected but R2 not configured. Falling back to local mode.")
            return "local"
    else:
        # Local development - default to local unless R2 is explicitly configured
        return "local"

SCREENSHOT_MODE = get_screenshot_mode()
print(f"📸 Screenshot serving mode: {SCREENSHOT_MODE}")

if API_KEY:
    CLIENT = OpenAI(api_key=API_KEY)
else:
    st.error("OPENAI_API_KEY not found. Please set it in .env.local or as an environment variable.")

def get_client():
    """Get the OpenAI client instance."""
    return CLIENT

def get_api_key():
    """Get the OpenAI API key."""
    return API_KEY

def get_chroma_config():
    """Get ChromaDB configuration based on environment."""
    return {
        "is_railway": IS_RAILWAY and CHROMA_HOST is not None,
        "host": CHROMA_HOST,
        "auth_token": CHROMA_AUTH_TOKEN
    }

def get_environment():
    """Get current environment (local or railway)."""
    return "railway" if IS_RAILWAY else "local"

def get_screenshot_config():
    """Get screenshot serving configuration."""
    return {
        "mode": SCREENSHOT_MODE,
        "is_r2": SCREENSHOT_MODE == "r2",
        "is_local": SCREENSHOT_MODE == "local"
    }

def get_r2_config():
    """Get R2 configuration for debugging."""
    return {
        "account_id": os.environ.get("R2_ACCOUNT_ID"),
        "bucket_name": os.environ.get("R2_BUCKET_NAME"),
        "endpoint_url": os.environ.get("R2_ENDPOINT_URL"),
        "access_key_configured": bool(os.environ.get("R2_ACCESS_KEY_ID")),
        "secret_key_configured": bool(os.environ.get("R2_SECRET_ACCESS_KEY")),
        "token_configured": bool(os.environ.get("R2_TOKEN"))
    }

def set_screenshot_mode(mode: str):
    """Manually set screenshot mode (for debug toggle)."""
    if mode in ["r2", "local"]:
        os.environ["SCREENSHOT_MODE"] = mode
        global SCREENSHOT_MODE
        SCREENSHOT_MODE = mode
        print(f"📸 Screenshot mode set to: {mode}")
    else:
        raise ValueError(f"Invalid screenshot mode: {mode}. Must be 'r2' or 'local'.") 