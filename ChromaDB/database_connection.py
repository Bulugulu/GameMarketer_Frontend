import pg8000.dbapi
import os
from dotenv import load_dotenv

class DatabaseConnection:
    def __init__(self):
        load_dotenv('.env.local')
        self.conn = pg8000.dbapi.connect(
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=int(os.getenv("PG_PORT", 5432)),
            database=os.getenv("PG_DATABASE")
        )
    
    def get_connection(self):
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close() 