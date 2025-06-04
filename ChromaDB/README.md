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

## 🔄 Enhanced Change Detection for Feature Embeddings

The feature embedding system now includes advanced change detection capabilities to automatically re-process features when their content has been updated.

### Change Detection Methods

**1. Content Hash (Default - Recommended)**
```bash
# Automatically detects when name or description content changes
python ChromaDB/generate_feature_embeddings.py --change-detection content_hash
```
- Compares SHA256 hash of name + description content
- Most accurate method for detecting meaningful changes
- Ignores irrelevant metadata changes (like timestamps)

**2. Timestamp-Based**
```bash
# Uses database updated_at timestamps to detect changes
python ChromaDB/generate_feature_embeddings.py --change-detection timestamp
```
- Compares `updated_at` field from database with stored timestamp
- Good for systems with reliable timestamp tracking
- May re-process features with metadata-only changes

**3. Force All (Re-process Everything)**
```bash
# Re-processes ALL features, ignoring existing embeddings
python ChromaDB/generate_feature_embeddings.py --change-detection force_all
```
- Useful for model upgrades or major system changes
- Will regenerate all embeddings (costs more API tokens)
- Ensures complete consistency

**4. Skip Existing (Traditional Resume)**
```bash
# Traditional mode - skips all features that already have embeddings
python ChromaDB/generate_feature_embeddings.py --change-detection skip_existing
```
- Legacy behavior for backward compatibility
- Only processes completely new features
- Fastest option when no changes are expected

### Practical Examples

**Daily/Regular Updates (Recommended)**
```bash
# Check for content changes and process only what's needed
python ChromaDB/generate_feature_embeddings.py
# Uses content_hash by default - efficient and accurate
```

**After Bulk Content Updates**
```bash
# Use timestamp detection if you know when changes occurred
python ChromaDB/generate_feature_embeddings.py --change-detection timestamp
```

**After Model/System Changes**
```bash
# Force regeneration of all embeddings
python ChromaDB/generate_feature_embeddings.py --change-detection force_all
```

**Quick Feature Addition Check**
```bash
# Process only completely new features (fast)
python ChromaDB/generate_feature_embeddings.py --change-detection skip_existing --limit 1000
```

### Understanding the Output

When you run the feature embedding generation, you'll see detailed statistics:

```
🔄 Enhanced resume analysis:
   📊 New features: 15        # Completely new features
   🔄 Changed features: 8     # Features with updated content
   ✅ Unchanged features (skipped): 1,247  # No changes detected
   📈 Total to process: 23    # Will generate embeddings for 23 features

🔍 Change detection method: content_hash
      • Feature 142: Updated building system mechanics now include...
      • Feature 298: Improved combat system with new weapon types...
      • ... and 6 more
```

### Change Detection Flow

1. **Query Database**: Fetch all features with timestamps
2. **Analyze Existing**: Get existing embeddings with metadata from ChromaDB
3. **Detect Changes**: Compare using selected method:
   - Content hash: Hash current name+description vs stored hash
   - Timestamp: Compare `updated_at` vs `last_updated` in metadata
   - Force all: Mark all as changed
   - Skip existing: Mark all existing as unchanged
4. **Process**: Generate embeddings only for new and changed features
5. **Update ChromaDB**: Store embeddings with enhanced metadata for future comparisons

### Metadata Stored for Change Detection

Each feature embedding now includes:
- `content_hash`: SHA256 hash of name + description
- `embedding_generated_at`: When the embedding was created
- `last_updated`: Database timestamp when feature was last modified
- `embedding_dimensions`: Vector dimensions used
- `model`: OpenAI model used for embedding
- `processing_success`: Whether embedding generation succeeded

### Integration with Existing Workflows

**Update Your CI/CD Pipeline**
```bash
# Add to your deployment script
echo "Updating feature embeddings..."
python ChromaDB/generate_feature_embeddings.py --change-detection content_hash

if [ $? -eq 0 ]; then
    echo "Updating vector database..."
    python ChromaDB/setup_vector_database.py
    echo "Vector database updated successfully"
fi
```

**Monitor Changes**
```bash
# Check what would change without processing
python ChromaDB/generate_feature_embeddings.py --change-detection content_hash --limit 0
# Shows analysis but processes 0 features
```

### Performance Considerations

- **Content Hash**: Fast analysis, accurate detection
- **Timestamp**: Very fast analysis, may over-process
- **Force All**: No analysis time, but processes everything
- **Skip Existing**: Fastest analysis and processing

### Troubleshooting

**Problem**: Too many features marked as "changed" 
**Solution**: Check if your database has reliable timestamps, consider using `content_hash` method

**Problem**: Missing content changes
**Solution**: Use `force_all` to regenerate everything, then switch to `content_hash` for future runs

**Problem**: Want to see what changed without processing
**Solution**: Run with `--limit 0` to see analysis without generating embeddings

## 🖼️ Enhanced Change Detection for Screenshot Embeddings

The screenshot embedding system includes the same advanced change detection capabilities as features, allowing you to efficiently re-process only screenshots that have changed.

### Screenshot Change Detection Methods

**1. Content Hash (Default - Recommended)**
```bash
# Automatically detects when caption, description, or UI elements change
python ChromaDB/generate_screenshot_embeddings.py --change-detection content_hash
```
- Compares SHA256 hash of caption + description + UI elements
- Most accurate method for detecting meaningful content changes
- Ignores irrelevant metadata changes

**2. Timestamp-Based**
```bash
# Uses database updated_at/last_updated timestamps
python ChromaDB/generate_screenshot_embeddings.py --change-detection timestamp
```
- Compares database timestamps with stored embedding metadata
- Good for systems with reliable timestamp tracking

**3. Force All & Skip Existing**
```bash
# Re-process all screenshots
python ChromaDB/generate_screenshot_embeddings.py --change-detection force_all

# Traditional resume (new screenshots only)
python ChromaDB/generate_screenshot_embeddings.py --change-detection skip_existing
```

### Screenshot-Specific Examples

**Daily Screenshot Updates**
```bash
# Process new and changed screenshots efficiently
python ChromaDB/generate_screenshot_embeddings.py
```

**After UI/Caption Updates**
```bash
# Detect screenshots with updated captions or UI elements
python ChromaDB/generate_screenshot_embeddings.py --change-detection content_hash
```

**After Screenshot Re-analysis**
```bash
# Force regeneration after updating screenshot analysis
python ChromaDB/generate_screenshot_embeddings.py --change-detection force_all
```

### Screenshot Content Hash Includes:
- **Caption**: Screenshot caption text
- **Description**: Screenshot description 
- **UI Elements**: Structured UI element data (buttons, menus, etc.)

### Screenshot Metadata for Change Detection:
- `content_hash`: Hash of caption + description + elements
- `elements_data`: Stored UI elements for reference
- `path`: Screenshot file path
- `capture_time`: When screenshot was taken
- `last_updated`: Database modification timestamp

### Combined Workflow

**Update Both Features and Screenshots**
```bash
# Process features first
python ChromaDB/generate_feature_embeddings.py --change-detection content_hash

# Then process screenshots
python ChromaDB/generate_screenshot_embeddings.py --change-detection content_hash

# Update vector database with both
python ChromaDB/setup_vector_database.py
```

**Parallel Processing for Large Datasets**
```bash
# Process in parallel for faster updates
python ChromaDB/generate_feature_embeddings.py --change-detection content_hash &
python ChromaDB/generate_screenshot_embeddings.py --change-detection content_hash &
wait  # Wait for both to complete
python ChromaDB/setup_vector_database.py
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
**Important**: Results use **cosine distance** scoring where **lower values = more similar**
- Distance typically ranges from 0.0 to 2.0 (cosine distance between normalized vectors)
- 0.0 = identical vectors (same direction), 2.0 = completely opposite vectors
- Results are automatically sorted by distance (ascending)
- **Cosine distance formula**: `distance = 1 - cosine_similarity`
- **Cosine similarity formula**: `cos(θ) = (A·B) / (|A|×|B|)`

```python
# Example distances with cosine metric
features = search.search_game_features("building construction")
for feature in features:
    if feature['distance'] < 0.3:
        print(f"Highly similar: {feature['name']}")
    elif feature['distance'] < 0.7:
        print(f"Moderately similar: {feature['name']}")
    elif feature['distance'] < 1.2:
        print(f"Somewhat similar: {feature['name']}")
    else:
        print(f"Less similar: {feature['name']}")
```

### Why Cosine Distance for Text Embeddings?
- **OpenAI embeddings** (`text-embedding-3-large`) are normalized to unit length
- **Cosine distance** measures the angle between vectors, focusing on semantic direction
- **Better semantic results** compared to L2 distance which measures coordinate differences
- **Ideal for text similarity** where meaning matters more than magnitude

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