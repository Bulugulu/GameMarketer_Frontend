"""
ChromaDB Vector Database Integration

This package provides vector database functionality for game features and screenshots
using ChromaDB with OpenAI embeddings.

Main classes:
- GameDataSearchInterface: Main interface for searching game data
- ChromaDBManager: Low-level ChromaDB operations
- FeatureEmbeddingsGenerator: Generate embeddings for game features
- ScreenshotEmbeddingsGenerator: Generate embeddings for screenshots
"""

from .vector_search_interface import GameDataSearchInterface
from .chromadb_manager import ChromaDBManager
from .feature_embeddings_generator import FeatureEmbeddingsGenerator
from .screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator

__version__ = "1.0.0"
__all__ = [
    "GameDataSearchInterface",
    "ChromaDBManager", 
    "FeatureEmbeddingsGenerator",
    "ScreenshotEmbeddingsGenerator"
] 