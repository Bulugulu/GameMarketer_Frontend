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

### 6. Inspect Database Structure
View ChromaDB structure and SQL correlation examples:
```bash
python ChromaDB/inspect_database_structure.py
```

## Database Structure & SQL Correlation

### ChromaDB Collections
- **game_features**: Game feature embeddings with SQL correlation
- **game_screenshots**: Screenshot embeddings with SQL correlation

### ID Mapping System
**ChromaDB Document IDs:**
- Features: `feature_{sql_feature_id}` (e.g., `feature_21`)
- Screenshots: `screenshot_{sql_screenshot_id}` (e.g., `screenshot_3f9011ec-...`)

**Metadata Contains Original SQL Data:**
- **Features**: `feature_id`, `name`, `description`, `game_id`, `type`, `token_count`, `created_at`
- **Screenshots**: `screenshot_id`, `path`, `caption`, `game_id`, `type`, `token_count`, `capture_time`, `created_at`

### SQL Correlation Example
```python
# Vector search result includes SQL IDs for correlation
{
    'type': 'feature',
    'feature_id': '21',           # ← Use this for SQL correlation
    'name': 'Construction Materials',
    'game_id': 'fd7d52c0-2231-48f4-aa9c-a22622cc5760',
    'distance': 1.0129,           # ← Lower distance = more similar
    'content': '...'
}

# Correlate to SQL database
cursor.execute("SELECT * FROM features_game WHERE feature_id = %s", (21,))
```

## Usage Examples

### Basic Search Interface
```python
from ChromaDB.vector_search_interface import GameDataSearchInterface

# Initialize search interface
search = GameDataSearchInterface()

# Search for game features (returns distance-based results)
features = search.search_game_features("farming agriculture crops", limit=5)
for feature in features:
    print(f"{feature['name']} - Distance: {feature['distance']:.3f}")
    print(f"SQL Feature ID: {feature['feature_id']}")  # For SQL correlation

# Search for screenshots
screenshots = search.search_game_screenshots("menu interface buttons", limit=5)
for screenshot in screenshots:
    print(f"{screenshot['path']} - Distance: {screenshot['distance']:.3f}")
    print(f"SQL Screenshot ID: {screenshot['screenshot_id']}")  # For SQL correlation

# Combined search
results = search.search_all_game_content("combat battle system", limit=10)
print(f"Found {len(results['features'])} features and {len(results['screenshots'])} screenshots")
```

### Distance-Based Scoring
**Important**: Results use **distance** scoring where **lower values = more similar**
- Distance typically ranges from 0.0 to 2.0 (cosine distance)
- 0.0 = identical, 2.0 = completely different
- Results are automatically sorted by distance (ascending)

```python
# Example distances
features = search.search_game_features("building construction")
for feature in features:
    if feature['distance'] < 0.5:
        print(f"Very similar: {feature['name']}")
    elif feature['distance'] < 1.0:
        print(f"Somewhat similar: {feature['name']}")
    else:
        print(f"Less similar: {feature['name']}")
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

### SQL Correlation Workflow
```python
from ChromaDB.vector_search_interface import GameDataSearchInterface
from ChromaDB.database_connection import DatabaseConnection

# 1. Perform vector search
search = GameDataSearchInterface()
results = search.search_game_features("farming agriculture", limit=5)

# 2. Extract SQL IDs and query database
db = DatabaseConnection()
conn = db.get_connection()
cursor = conn.cursor()

for result in results:
    feature_id = result['feature_id']
    distance = result['distance']
    
    # Get full record from SQL database
    cursor.execute("SELECT * FROM features_game WHERE feature_id = %s", (feature_id,))
    sql_record = cursor.fetchone()
    
    print(f"Vector distance: {distance:.3f}")
    print(f"SQL record: {sql_record}")
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
├── inspect_database_structure.py       # Inspect ChromaDB structure and SQL correlation
├── chroma_db/                          # ChromaDB storage (created automatically)
├── feature_embeddings.json            # Generated feature embeddings
└── screenshot_embeddings.json         # Generated screenshot embeddings
```

## Scripts

### Database Inspection
```bash
# Inspect ChromaDB structure and see SQL correlation examples
python ChromaDB/inspect_database_structure.py
```

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
from ChromaDB.vector_search_interface import GameDataSearchInterface

# Initialize once (use session state to cache)
if 'search_interface' not in st.session_state:
    st.session_state.search_interface = GameDataSearchInterface()

# Use in your app
query = st.text_input("Search game features:")
if query:
    results = st.session_state.search_interface.search_game_features(query)
    for result in results:
        st.write(f"**{result['name']}** - Distance: {result['distance']:.3f}")
        st.write(f"Feature ID: {result['feature_id']} | Game: {result['game_id']}")
        st.write(result['description'])
```

### In Agents/Tools
```python
from ChromaDB.vector_search_interface import GameDataSearchInterface

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

def extract_sql_ids_from_results(results):
    """Extract SQL IDs for database correlation"""
    sql_ids = []
    for result in results:
        if result['type'] == 'feature':
            sql_ids.append(('feature', result['feature_id']))
        elif result['type'] == 'screenshot':
            sql_ids.append(('screenshot', result['screenshot_id']))
    return sql_ids
```

## Performance Notes

- **Embedding Generation**: Uses OpenAI's `text-embedding-3-large` model
- **Token Costs**: Monitor OpenAI usage - each text piece gets embedded
- **ChromaDB Storage**: Persistent storage in `ChromaDB/chroma_db/`
- **Batch Processing**: Embeddings are processed and stored in batches
- **Search Speed**: ChromaDB provides fast vector similarity search
- **SQL Correlation**: All vector results include original SQL IDs for easy correlation

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

# Inspect database structure
python ChromaDB/inspect_database_structure.py
```

## Cost Estimation

OpenAI embedding costs (approximate):
- **text-embedding-3-large**: $0.00013 per 1K tokens
- Average text length: ~50-200 tokens per item
- Example: 1,000 features + 1,000 screenshots ≈ $0.02-0.05

Monitor your usage and start with `--test` mode for development. 