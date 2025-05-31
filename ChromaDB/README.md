# ChromaDB Vector Database Integration

This directory contains a complete ChromaDB vector database integration for searching game features and screenshots using semantic search with OpenAI embeddings.

## Quick Start

### 1. Install Dependencies
Make sure you have the updated requirements installed:
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Ensure your `.env.local` file contains:
```
# Database connection
PG_USER=your_postgres_user
PG_PASSWORD=your_postgres_password
PG_HOST=your_postgres_host
PG_PORT=5432
PG_DATABASE=your_database_name

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
```

### 3. Quick Setup (Test Mode)
Run the complete setup with limited data for testing:
```bash
python ChromaDB/setup_vector_database.py --test
```

### 4. Full Setup
For production with all your data:
```bash
python ChromaDB/setup_vector_database.py
```

### 5. Test the System
```bash
python ChromaDB/test_vector_search.py
```

## Usage Examples

### Basic Search Interface
```python
from ChromaDB import GameDataSearchInterface

# Initialize search interface
search = GameDataSearchInterface()

# Search for game features
features = search.search_game_features("farming agriculture crops", limit=5)
for feature in features:
    print(f"{feature['name']} - Score: {feature['relevance_score']:.3f}")

# Search for screenshots
screenshots = search.search_game_screenshots("menu interface buttons", limit=5)
for screenshot in screenshots:
    print(f"{screenshot['path']} - Score: {screenshot['relevance_score']:.3f}")

# Combined search
results = search.search_all_game_content("combat battle system", limit=10)
print(f"Found {len(results['features'])} features and {len(results['screenshots'])} screenshots")
```

### Game-Specific Search
```python
# Search within a specific game
features = search.search_game_features(
    query="building construction", 
    limit=5, 
    game_id="your-game-id"
)
```

## File Structure

```
ChromaDB/
├── __init__.py                          # Package initialization
├── README.md                            # This file
├── ImplementationSteps.md               # Detailed implementation guide
├── database_connection.py               # PostgreSQL connection utility
├── feature_embeddings_generator.py     # Generate feature embeddings
├── screenshot_embeddings_generator.py  # Generate screenshot embeddings
├── chromadb_manager.py                 # ChromaDB operations
├── vector_search_interface.py          # Main search interface
├── generate_feature_embeddings.py      # Script to generate feature embeddings
├── generate_screenshot_embeddings.py   # Script to generate screenshot embeddings
├── setup_vector_database.py            # Complete setup script
├── test_vector_search.py               # Test script
├── chroma_db/                          # ChromaDB storage (created automatically)
├── feature_embeddings.json            # Generated feature embeddings
└── screenshot_embeddings.json         # Generated screenshot embeddings
```

## Scripts

### Individual Scripts
```bash
# Generate only feature embeddings
python ChromaDB/generate_feature_embeddings.py --limit 100

# Generate only screenshot embeddings  
python ChromaDB/generate_screenshot_embeddings.py --limit 50

# Generate for specific game
python ChromaDB/generate_feature_embeddings.py --game-id "your-game-id"
```

### Setup Options
```bash
# Test mode (limited data)
python ChromaDB/setup_vector_database.py --test

# Limited production run
python ChromaDB/setup_vector_database.py --limit-features 1000 --limit-screenshots 500

# Specific game setup
python ChromaDB/setup_vector_database.py --game-id "your-game-id"

# Full production setup (all data)
python ChromaDB/setup_vector_database.py
```

## Integration with Your Application

### In Streamlit Apps
```python
import streamlit as st
from ChromaDB import GameDataSearchInterface

# Initialize once (use session state to cache)
if 'search_interface' not in st.session_state:
    st.session_state.search_interface = GameDataSearchInterface()

# Use in your app
query = st.text_input("Search game features:")
if query:
    results = st.session_state.search_interface.search_game_features(query)
    for result in results:
        st.write(f"**{result['name']}** - Score: {result['relevance_score']:.3f}")
        st.write(result['description'])
```

### In Agents/Tools
```python
from ChromaDB import GameDataSearchInterface

def search_game_content_tool(query: str, content_type: str = "both") -> str:
    """Tool for agents to search game content"""
    search = GameDataSearchInterface()
    
    if content_type == "features":
        results = search.search_game_features(query)
        return format_feature_results(results)
    elif content_type == "screenshots":
        results = search.search_game_screenshots(query)
        return format_screenshot_results(results)
    else:
        results = search.search_all_game_content(query)
        return format_combined_results(results)
```

## Performance Notes

- **Embedding Generation**: Uses OpenAI's `text-embedding-3-large` model
- **Token Costs**: Monitor OpenAI usage - each text piece gets embedded
- **ChromaDB Storage**: Persistent storage in `ChromaDB/chroma_db/`
- **Batch Processing**: Embeddings are processed and stored in batches
- **Search Speed**: ChromaDB provides fast vector similarity search

## Troubleshooting

### Common Issues
1. **Import Errors**: Make sure you're running scripts from the project root
2. **Database Connection**: Verify your `.env.local` PostgreSQL credentials
3. **OpenAI API**: Check your API key and account limits
4. **Memory Usage**: Use `--limit` flags for large datasets

### Debugging
```bash
# Test database connection
python -c "from ChromaDB.database_connection import DatabaseConnection; db = DatabaseConnection(); print('✓ Database connected')"

# Test OpenAI API
python -c "import openai; import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print('✓ OpenAI API key loaded')"

# Check ChromaDB status
python ChromaDB/test_vector_search.py
```

## Cost Estimation

OpenAI embedding costs (approximate):
- **text-embedding-3-large**: $0.00013 per 1K tokens
- Average text length: ~50-200 tokens per item
- Example: 1,000 features + 1,000 screenshots ≈ $0.02-0.05

Monitor your usage and start with `--test` mode for development. 