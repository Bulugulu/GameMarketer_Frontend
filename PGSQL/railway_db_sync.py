#!/usr/bin/env python3
"""
Railway Database Synchronization Script

This script will:
1. Dump the local PostgreSQL database
2. Upload it to Railway
3. Verify the upload was successful

Requirements:
- pg_dump and psql must be available in PATH
- .env.local must contain DATABASE_PUBLIC_URL and local PG_* variables
"""

import os
import sys
import subprocess
import tempfile
import time
from datetime import datetime
from dotenv import load_dotenv
import pg8000
from urllib.parse import urlparse

# Load environment variables
load_dotenv("../.env.local")

class DatabaseSyncError(Exception):
    """Custom exception for database sync operations"""
    pass

class RailwayDBSync:
    def __init__(self):
        # Initialize instance variables first
        self.dump_file = None
        self.log_messages = []
        
        # Local DB: Uses separate PG* environment variables
        # Railway DB: Uses single DATABASE_PUBLIC_URL that contains everything
        self.local_config = self._get_local_config()
        self.railway_config = self._get_railway_config()
    
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        print(log_msg)
        self.log_messages.append(log_msg)
    
    def _get_local_config(self):
        """Extract local PostgreSQL configuration from environment variables"""
        # Check for the specific environment variables used by this project
        config = {
            'host': os.getenv('PG_HOST', 'localhost'),
            'port': os.getenv('PG_PORT', '5432'),
            'database': os.getenv('PG_DATABASE'),
            'user': os.getenv('PG_USER'),
            'password': os.getenv('PG_PASSWORD') or os.getenv('DATABASE_PASSWORD')
        }
        
        missing = [k for k, v in config.items() if not v]
        if missing:
            self.log("Checking environment variables for local database config...", "DEBUG")
            self.log(f"Available vars: PG_DATABASE={os.getenv('PG_DATABASE')}, PG_USER={os.getenv('PG_USER')}, PG_HOST={os.getenv('PG_HOST')}, PG_PORT={os.getenv('PG_PORT')}", "DEBUG")
            self.log(f"Password vars: PG_PASSWORD={'***' if os.getenv('PG_PASSWORD') else None}, DATABASE_PASSWORD={'***' if os.getenv('DATABASE_PASSWORD') else None}", "DEBUG")
            raise DatabaseSyncError(f"Missing local DB config: {', '.join(missing)}. Need PG_DATABASE, PG_USER, PG_HOST, PG_PORT, and PG_PASSWORD (or DATABASE_PASSWORD) for LOCAL database connection.")
        
        self.log(f"Local DB config loaded: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        return config
    
    def _get_railway_config(self):
        """Extract Railway PostgreSQL configuration from DATABASE_PUBLIC_URL"""
        url = os.getenv('DATABASE_PUBLIC_URL')
        if not url:
            raise DatabaseSyncError("DATABASE_PUBLIC_URL not found in environment variables")
        
        try:
            parsed = urlparse(url)
            config = {
                'host': parsed.hostname,
                'port': str(parsed.port or 5432),
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
                'url': url
            }
            
            self.log(f"Railway DB config loaded: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
            return config
        except Exception as e:
            raise DatabaseSyncError(f"Failed to parse DATABASE_PUBLIC_URL: {e}")
    
    def test_connection(self, config, name):
        """Test database connection"""
        try:
            conn = pg8000.connect(
                host=config['host'],
                port=int(config['port']),
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
            conn.close()
            self.log(f"✓ {name} connection successful")
            return True
        except Exception as e:
            self.log(f"✗ {name} connection failed: {e}", "ERROR")
            return False
    
    def dump_local_database(self):
        """Create a dump of the local database"""
        try:
            # Create temporary file for dump
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.dump_file = f"township_db_dump_{timestamp}.sql"
            dump_path = os.path.join(tempfile.gettempdir(), self.dump_file)
            
            self.log(f"Creating database dump: {dump_path}")
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                f"--host={self.local_config['host']}",
                f"--port={self.local_config['port']}",
                f"--username={self.local_config['user']}",
                f"--dbname={self.local_config['database']}",
                '--verbose',
                '--clean',
                '--no-owner',
                '--no-privileges',
                '--format=plain',
                f"--file={dump_path}"
            ]
            
            # Set password environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.local_config['password']
            
            # Execute pg_dump
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise DatabaseSyncError(f"pg_dump failed: {result.stderr}")
            
            # Check if dump file was created and has content
            if not os.path.exists(dump_path) or os.path.getsize(dump_path) == 0:
                raise DatabaseSyncError("Dump file was not created or is empty")
            
            file_size = os.path.getsize(dump_path) / (1024 * 1024)  # MB
            self.log(f"✓ Database dump created successfully ({file_size:.2f} MB)")
            
            return dump_path
            
        except subprocess.CalledProcessError as e:
            raise DatabaseSyncError(f"Failed to dump database: {e}")
        except Exception as e:
            raise DatabaseSyncError(f"Unexpected error during dump: {e}")
    
    def upload_to_railway(self, dump_path):
        """Upload the database dump to Railway"""
        try:
            self.log("Uploading dump to Railway database...")
            
            # Build psql command for Railway
            cmd = [
                'psql',
                self.railway_config['url'],
                '--file', dump_path,
                '--echo-errors',
                '--quiet'
            ]
            
            # Execute psql
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise DatabaseSyncError(f"psql upload failed: {result.stderr}")
            
            self.log("✓ Database uploaded to Railway successfully")
            
        except subprocess.CalledProcessError as e:
            raise DatabaseSyncError(f"Failed to upload to Railway: {e}")
        except Exception as e:
            raise DatabaseSyncError(f"Unexpected error during upload: {e}")
    
    def get_table_counts(self, config):
        """Get row counts for all tables"""
        try:
            conn = pg8000.connect(
                host=config['host'],
                port=int(config['port']),
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            counts = {}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            
            conn.close()
            return counts
            
        except Exception as e:
            self.log(f"Error getting table counts: {e}", "ERROR")
            return {}
    
    def verify_sync(self):
        """Verify that the sync was successful"""
        self.log("Verifying database synchronization...")
        
        # Get table counts from both databases
        local_counts = self.get_table_counts(self.local_config)
        railway_counts = self.get_table_counts(self.railway_config)
        
        if not local_counts or not railway_counts:
            raise DatabaseSyncError("Failed to get table counts for verification")
        
        # Compare table counts
        self.log("\nTable count comparison:")
        self.log("=" * 50)
        self.log(f"{'Table':<25} {'Local':<10} {'Railway':<10} {'Status'}")
        self.log("=" * 50)
        
        all_tables = set(local_counts.keys()) | set(railway_counts.keys())
        mismatches = []
        
        for table in sorted(all_tables):
            local_count = local_counts.get(table, 0)
            railway_count = railway_counts.get(table, 0)
            
            if local_count == railway_count:
                status = "✓ MATCH"
            else:
                status = "✗ MISMATCH"
                mismatches.append(table)
            
            self.log(f"{table:<25} {local_count:<10} {railway_count:<10} {status}")
        
        self.log("=" * 50)
        
        if mismatches:
            raise DatabaseSyncError(f"Table count mismatches found: {', '.join(mismatches)}")
        
        self.log("✓ All table counts match - synchronization verified!")
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.dump_file:
            dump_path = os.path.join(tempfile.gettempdir(), self.dump_file)
            try:
                if os.path.exists(dump_path):
                    os.remove(dump_path)
                    self.log(f"✓ Cleaned up dump file: {dump_path}")
            except Exception as e:
                self.log(f"Warning: Failed to clean up dump file: {e}", "WARNING")
    
    def run_sync(self):
        """Execute the complete synchronization process"""
        try:
            self.log("=" * 60)
            self.log("RAILWAY DATABASE SYNCHRONIZATION STARTED")
            self.log("=" * 60)
            
            # Test connections
            self.log("Testing database connections...")
            if not self.test_connection(self.local_config, "Local"):
                raise DatabaseSyncError("Cannot connect to local database")
            
            if not self.test_connection(self.railway_config, "Railway"):
                raise DatabaseSyncError("Cannot connect to Railway database")
            
            # Dump local database
            dump_path = self.dump_local_database()
            
            # Upload to Railway
            self.upload_to_railway(dump_path)
            
            # Verify synchronization
            self.verify_sync()
            
            self.log("=" * 60)
            self.log("✓ DATABASE SYNCHRONIZATION COMPLETED SUCCESSFULLY!")
            self.log("=" * 60)
            
        except DatabaseSyncError as e:
            self.log(f"Synchronization failed: {e}", "ERROR")
            return False
        except KeyboardInterrupt:
            self.log("Synchronization interrupted by user", "WARNING")
            return False
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            return False
        finally:
            self.cleanup()
        
        return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print(__doc__)
        return
    
    try:
        sync = RailwayDBSync()
        success = sync.run_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 