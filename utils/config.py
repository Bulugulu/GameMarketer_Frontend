import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(".env.local")

# Initialize OpenAI client
API_KEY = os.environ.get("OPENAI_API_KEY")
CLIENT = None
MODEL_NAME = "gpt-4o"  # Use a model that works well with Agents SDK

# Global variable for the database connection parameters
DB_CONNECTION_PARAMS = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "dbname": os.environ.get("DB_NAME", "township_db"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "port": os.environ.get("DB_PORT", "5432")
}

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