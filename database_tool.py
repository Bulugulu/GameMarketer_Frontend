import pg8000
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env.local, especially for DB credentials
load_dotenv(".env.local")

def run_sql_query(query: str) -> dict:
    """
    Run a SQL SELECT query using pg8000 and return results as a dict.
    Database connection parameters are automatically determined based on environment
    (local development vs Railway deployment).
    """
    try:
        # Use centralized database configuration
        from utils.config import DB_CONNECTION_PARAMS, get_environment
        
        db_params = DB_CONNECTION_PARAMS
        environment = get_environment()
        
        print(f"[DEBUG] Database connection for {environment} environment:")
        print(f"[DEBUG] Host: {db_params['host']}, Database: {db_params['dbname']}")
        
        if not all([db_params['dbname'], db_params['user'], db_params['password']]):
            missing = [k for k, v in db_params.items() if not v and k != 'port']
            return {"error": f"Database credentials missing: {missing}. Environment: {environment}"}
            
    except ImportError:
        # Fallback to original logic if utils.config is not available
        print("[DEBUG] Falling back to direct environment variable reading")
        db_params = {
            'dbname': os.environ.get("PG_DATABASE"),
            'user': os.environ.get("PG_USER"),
            'password': os.environ.get("PG_PASSWORD") or os.environ.get("DATABASE_PASSWORD"),
            'host': os.environ.get("PG_HOST", "localhost"),
            'port': int(os.environ.get("PG_PORT", "5432"))
        }
        
        if not all([db_params['dbname'], db_params['user'], db_params['password']]):
            return {"error": "Database credentials (PG_DATABASE, PG_USER, PG_PASSWORD or DATABASE_PASSWORD) not found in environment variables."}

    conn = None  # Initialize conn to None
    try:
        conn = pg8000.connect(
            database=db_params['dbname'],
            user=db_params['user'],
            password=db_params['password'],
            host=db_params['host'],
            port=int(db_params['port'])
        )
        cursor = conn.cursor()

        # Safety check: Only allow SELECT statements
        if not query.strip().lower().startswith("select"):
            return {"error": "Only SELECT statements are allowed."}

        cursor.execute(query)
        
        if cursor.description is None: # Check if the query returned any rows (e.g. SELECT on empty table, or non-row returning statements)
            return {
                "columns": [],
                "rows": []
            }
            
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        # Attempt to serialize rows to JSON to catch potential issues early
        # pg8000 might return types that are not directly JSON serializable (e.g., datetime)
        # For simplicity, we'll convert them to strings here.
        # A more robust solution might involve custom encoders or type checking.
        serializable_rows = []
        for row in rows:
            serializable_row = []
            for item in row:
                if hasattr(item, 'isoformat'): # For datetime, date objects
                    serializable_row.append(item.isoformat())
                else:
                    serializable_row.append(item)
            serializable_rows.append(serializable_row)

        return {
            "columns": columns,
            "rows": serializable_rows,
            "message": f"Query executed successfully. Found {len(serializable_rows)} rows."
        }
    except pg8000.Error as e:
        return {"error": f"Database error: {str(e)}"}
    except ValueError as ve: # Catch the ValueError from the safety check
        return {"error": str(ve)}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}
    finally:
        if conn: # Only try to close if connection was successfully established
            # cursor.close() # cursor is closed automatically when it goes out of scope if 'with' statement isn't used. Or if conn.close() is called.
            conn.close()

if __name__ == '__main__':
    # Example usage with automatic environment detection
    print("Attempting to run a sample query against the 'screens' table...")
    
    # Test the centralized configuration
    try:
        from utils.config import get_environment, DB_CONNECTION_PARAMS
        env = get_environment()
        print(f"Detected environment: {env}")
        print(f"Database configuration: {DB_CONNECTION_PARAMS['host']}:{DB_CONNECTION_PARAMS['port']}/{DB_CONNECTION_PARAMS['dbname']}")
        
        test_query = "SELECT id, screen_id, screen_name, screen_type FROM screens LIMIT 2;"
        results = run_sql_query(test_query)
        print("\nQuery Results:")
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print(f"Columns: {results['columns']}")
            for row in results['rows']:
                print(row)
            print(f"Message: {results.get('message', '')}")
            
    except ImportError as e:
        print(f"Could not import utils.config: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"Configuration error: {e}")

    # Test non-SELECT query
    print("\nAttempting to run a non-SELECT query (should be blocked)...")
    non_select_query = "DROP TABLE screens;"
    results_non_select = run_sql_query(non_select_query)
    print(f"Non-SELECT Query Results: {results_non_select}")
    if "error" in results_non_select and "Only SELECT statements are allowed" in results_non_select["error"]:
        print("Correctly blocked non-SELECT statement.")
    else:
        print("Failed to block non-SELECT statement or other error occurred.") 