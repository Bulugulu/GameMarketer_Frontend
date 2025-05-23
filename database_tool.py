import pg8000
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env.local, especially for DB credentials
load_dotenv(".env.local")

def run_sql_query(query: str) -> dict:
    """
    Run a SQL SELECT query using pg8000 and return results as a dict.
    Database connection parameters are read from environment variables:
    PG_DATABASE, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT.
    """
    db_name = os.environ.get("PG_DATABASE")
    user = os.environ.get("PG_USER")
    password = os.environ.get("PG_PASSWORD")
    host = os.environ.get("PG_HOST", "localhost")
    port = int(os.environ.get("PG_PORT", 5432))

    if not all([db_name, user, password]):
        return {"error": "Database credentials (PG_DATABASE, PG_USER, PG_PASSWORD) not found in environment variables."}

    conn = None  # Initialize conn to None
    try:
        conn = pg8000.connect(
            database=db_name,
            user=user,
            password=password,
            host=host,
            port=port
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
    # Example usage (ensure your .env.local is set up with PG_* variables)
    # Create a dummy .env.local if you don't have one:
    # PG_DATABASE=your_db
    # PG_USER=your_user
    # PG_PASSWORD=your_password
    # PG_HOST=localhost
    # PG_PORT=5432
    
    # Note: You'll need a PostgreSQL server running and the specified database/table existing.
    # For this example, let's assume a table 'screens' exists based on the user's context.
    # A more comprehensive test would involve setting up a test DB.

    print("Attempting to run a sample query against the 'screens' table...")
    # Replace 'your_screens_table_name' with the actual table name if different
    # Ensure your DB has a table that matches the structure provided by the user.
    # Example based on user's `database_structure_md` for the `screens` table
    test_query = "SELECT id, screen_id, screen_name, screen_type FROM screens LIMIT 2;" 
    
    # Check if environment variables are loaded for the test
    if not all([os.environ.get("PG_DATABASE"), os.environ.get("PG_USER"), os.environ.get("PG_PASSWORD")]):
        print("Skipping example query: PG_DATABASE, PG_USER, or PG_PASSWORD not set in .env.local")
    else:
        results = run_sql_query(test_query)
        print("\nQuery Results:")
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print(f"Columns: {results['columns']}")
            for row in results['rows']:
                print(row)
            print(f"Message: {results.get('message', '')}")

    # Test non-SELECT query
    print("\nAttempting to run a non-SELECT query (should be blocked)...")
    non_select_query = "DROP TABLE screens;"
    results_non_select = run_sql_query(non_select_query)
    print(f"Non-SELECT Query Results: {results_non_select}")
    if "error" in results_non_select and "Only SELECT statements are allowed" in results_non_select["error"]:
        print("Correctly blocked non-SELECT statement.")
    else:
        print("Failed to block non-SELECT statement or other error occurred.") 