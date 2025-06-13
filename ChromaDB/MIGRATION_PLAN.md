## **Migration Plan: ChromaDB Embedding Pipeline to Backend**

This document outlines the steps to transfer the functionality for generating, ingesting, and managing ChromaDB vector embeddings from the frontend project to a dedicated backend service. The backend will connect to a Railway-hosted PostgreSQL database and a Railway-hosted ChromaDB instance.

### **Phase 1: Environment Setup and Configuration**

The first step is to ensure the backend service has the necessary configuration and credentials to connect to all external services.

**1.1. Required Environment Variables:**

The backend application must be configured with the following environment variables. These are based on the `database_connection.py` script and the common requirements for connecting to OpenAI and a remote ChromaDB instance.

*   **PostgreSQL (Railway Instance):**
    *   `PG_USER`: Username for the PostgreSQL database.
    *   `PG_PASSWORD`: Password for the PostgreSQL database.
    *   `PG_HOST`: Hostname of the Railway PostgreSQL instance.
    *   `PG_PORT`: Port for the Railway PostgreSQL instance (e.g., `5432`).
    *   `PG_DATABASE`: The name of the database.

*   **OpenAI API:**
    *   `OPENAI_API_KEY`: Your secret key for the OpenAI API, used for generating embeddings.

*   **ChromaDB (Railway Instance):**
    *   `CHROMA_HOST`: The public URL or IP address of your Railway ChromaDB service.
    *   `CHROMA_PORT`: The port your ChromaDB instance is listening on (e.g., `8000`).
    *   `CHROMA_SSL_ENABLED`: Set to `true` or `false` depending on your ChromaDB's SSL configuration on Railway.

**1.2. Backend Dependencies:**

The backend service will require the following Python libraries. A `requirements.txt` file should be created with these dependencies:

```
# requirements.txt
psycopg2-binary
python-dotenv
openai
chromadb
numpy
pandas
tqdm
```

### **Phase 2: Porting Core Logic**

The next phase involves migrating the essential Python modules from the frontend's `ChromaDB` directory to the backend's codebase.

**2.1. Files to Migrate:**

The logic within the following files should be adapted and moved to the backend. It's recommended to place them in a dedicated module (e.g., `backend.services.embedding_service`).

*   `ChromaDB/database_connection.py`: The `DatabaseConnection` class should be ported to handle connections to the Railway PostgreSQL instance using the environment variables defined above.
*   `ChromaDB/chromadb_manager.py`: The `ChromaDBManager` class is critical. It must be updated to connect to the remote Railway ChromaDB instance using an `HttpClient`. The connection logic should be modified to use the `CHROMA_HOST` and `CHROMA_PORT` environment variables.
*   `ChromaDB/feature_embeddings_generator.py`: This contains the core logic for processing game features. The `FeatureEmbeddingsGenerator` class, including its change detection mechanisms (`content_hash`, `timestamp`, etc.), should be ported.
*   `ChromaDB/screenshot_embeddings_generator.py`: Similarly, the `ScreenshotEmbeddingsGenerator` class and its logic should be ported to handle screenshot embeddings.
*   `ChromaDB/vector_search_interface.py`: The `GameDataSearchInterface` is essential for the verification step and for any future backend features that require semantic search. It should also be configured to use the remote ChromaDB connection.

### **Phase 3: Implementing the Backend Ingestion Workflow**

This phase details the end-to-end process for the backend service to generate and upload embeddings. This could be implemented as a scheduled task, a manually triggered job, or a long-running service.

**3.1. Workflow Steps:**

1.  **Initialization:**
    *   Load all environment variables.
    *   Instantiate the `DatabaseConnection` to connect to PostgreSQL.
    *   Instantiate the `ChromaDBManager` to connect to the Railway ChromaDB instance. Ensure the manager is configured to use the `game_features` and `game_screenshots` collections.

2.  **Process Game Features:**
    *   Instantiate `FeatureEmbeddingsGenerator`.
    *   Fetch all existing feature embeddings' metadata from the `game_features` collection in ChromaDB. This is crucial for the change detection step. The metadata should include the `content_hash` and the original `feature_id`.
    *   Fetch all game features from the PostgreSQL database (`features_game` table).
    *   **Implement Change Detection (as per `README.md`):**
        *   Iterate through the features from PostgreSQL.
        *   For each feature, generate a `content_hash` from its `name` and `description` fields.
        *   Compare this new hash with the hash stored in the metadata fetched from ChromaDB.
        *   Identify three lists of features:
            1.  **New:** Features present in PostgreSQL but not in ChromaDB.
            2.  **Changed:** Features where the `content_hash` differs between PostgreSQL and ChromaDB.
            3.  **Unchanged:** Features with matching hashes.
    *   Generate new embeddings using the OpenAI `text-embedding-3-large` model for only the **New** and **Changed** features.
    *   **Upsert to ChromaDB:**
        *   Prepare the data in the format required by ChromaDB. The ChromaDB document ID must be `f"feature_{sql_feature_id}"`.
        *   The metadata for each embedding must include the `feature_id`, `game_id`, `content_hash`, and other relevant fields as detailed in the `README.md`.
        *   Use the `ChromaDBManager` to perform a batch `upsert` operation into the `game_features` collection. Upserting correctly handles both adding new documents and updating existing ones.

3.  **Process Game Screenshots:**
    *   Follow the exact same workflow as in step 3.2, but using the `ScreenshotEmbeddingsGenerator`, the `game_screenshots` ChromaDB collection, and the corresponding tables and fields from PostgreSQL. The `content_hash` for screenshots should be based on `caption`, `description`, and `ui_elements`. The ChromaDB document ID should be `f"screenshot_{sql_screenshot_id}"`.

4.  **Logging and Reporting:**
    *   Throughout the process, log key statistics, including the number of new, changed, and skipped items for both features and screenshots. This provides visibility into the ingestion process.

### **Phase 4: Verification and Testing**

After the ingestion workflow is implemented, it's crucial to verify its correctness. A dedicated testing script should be created in the backend.

**4.1. Verification Script (`test_embedding_pipeline.py`):**

1.  **Connect:** Initialize and connect to the Railway ChromaDB instance using the `GameDataSearchInterface`.
2.  **Count Collections:**
    *   Query the `game_features` and `game_screenshots` collections.
    *   Print the total number of items in each collection to verify that data has been ingested.
3.  **Perform a Semantic Search:**
    *   Choose a specific term you expect to yield results (e.g., "crafting system" or "main menu UI").
    *   Use `search_game_features()` and `search_game_screenshots()` from the `GameDataSearchInterface`.
    *   Print the top 5 results for each search.
4.  **Verify Content and Correlation:**
    *   Examine the search results. They should be relevant to the search term.
    *   Check that the metadata in the results contains the correct SQL `feature_id` or `screenshot_id`. This confirms that the ID mapping system for SQL correlation is working correctly.
    *   The `distance` score should be present, indicating a successful vector search.

By following this plan, a coding agent can systematically migrate your embedding pipeline to the backend, ensuring it is robust, efficient, and verifiable. 