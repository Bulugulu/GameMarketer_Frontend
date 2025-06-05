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
    # Use Railway ChromaDB URL
    CHROMA_HOST = os.environ.get("CHROMA_PRIVATE_URL", "http://chroma.railway.internal")
    CHROMA_AUTH_TOKEN = os.environ.get("CHROMA_SERVER_AUTHN_CREDENTIALS", "")
else:
    # Use local ChromaDB (file-based) regardless of what Railway variables might be present
    CHROMA_HOST = None  # Will use local file-based ChromaDB
    CHROMA_AUTH_TOKEN = None

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
        "host": CHROMA_HOST,
        "auth_token": CHROMA_AUTH_TOKEN,
        "is_railway": IS_RAILWAY
    }

def get_environment():
    """Get current environment (local or railway)."""
    return "railway" if IS_RAILWAY else "local" 