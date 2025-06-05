#!/usr/bin/env python3
"""
Database Sync Verification Script

This script compares the local PostgreSQL database with the Railway database
to verify they are in sync. It checks:
- Table existence
- Row counts
- Basic schema information

Usage: python verify_sync.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import pg8000
from urllib.parse import urlparse

# Load environment variables
load_dotenv("../.env.local")

class DatabaseVerifier:
    def __init__(self):
        self.local_config = self._get_local_config()
        self.railway_config = self._get_railway_config()
    
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def _get_local_config(self):
        """Extract local PostgreSQL configuration"""
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
            raise ValueError(f"Missing local DB config: {', '.join(missing)}. Need PG_DATABASE, PG_USER, PG_HOST, PG_PORT, and PG_PASSWORD (or DATABASE_PASSWORD) for LOCAL database connection.")
        
        return config
    
    def _get_railway_config(self):
        """Extract Railway PostgreSQL configuration"""
        url = os.getenv('DATABASE_PUBLIC_URL')
        if not url:
            raise ValueError("DATABASE_PUBLIC_URL not found in environment variables")
        
        parsed = urlparse(url)
        return {
            'host': parsed.hostname,
            'port': str(parsed.port or 5432),
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password
        }
    
    def get_database_info(self, config, name):
        """Get comprehensive database information"""
        try:
            conn = pg8000.connect(
                host=config['host'],
                port=int(config['port']),
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
            cursor = conn.cursor()
            
            # Get tables and their row counts
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get row counts
            table_counts = {}
            total_rows = 0
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
                total_rows += count
            
            # Get database size
            cursor.execute(f"SELECT pg_size_pretty(pg_database_size('{config['database']}'))")
            db_size = cursor.fetchone()[0]
            
            # Get schema version (if exists)
            schema_version = None
            try:
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
                result = cursor.fetchone()
                if result:
                    schema_version = result[0]
            except:
                pass  # Table doesn't exist
            
            conn.close()
            
            return {
                'connected': True,
                'tables': tables,
                'table_counts': table_counts,
                'total_tables': len(tables),
                'total_rows': total_rows,
                'database_size': db_size,
                'schema_version': schema_version
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def compare_databases(self):
        """Compare local and railway databases"""
        self.log("=" * 60)
        self.log("DATABASE SYNCHRONIZATION VERIFICATION")
        self.log("=" * 60)
        
        # Get info from both databases
        self.log("Connecting to local database...")
        local_info = self.get_database_info(self.local_config, "Local")
        
        self.log("Connecting to Railway database...")
        railway_info = self.get_database_info(self.railway_config, "Railway")
        
        # Check connections
        if not local_info['connected']:
            self.log(f"✗ Local database connection failed: {local_info['error']}", "ERROR")
            return False
        
        if not railway_info['connected']:
            self.log(f"✗ Railway database connection failed: {railway_info['error']}", "ERROR")
            return False
        
        self.log("✓ Connected to both databases successfully")
        
        # Display summary information
        self.log("\nDatabase Summary:")
        self.log("=" * 40)
        self.log(f"{'Metric':<20} {'Local':<15} {'Railway':<15}")
        self.log("=" * 40)
        self.log(f"{'Tables':<20} {local_info['total_tables']:<15} {railway_info['total_tables']:<15}")
        self.log(f"{'Total Rows':<20} {local_info['total_rows']:<15} {railway_info['total_rows']:<15}")
        self.log(f"{'Database Size':<20} {local_info['database_size']:<15} {railway_info['database_size']:<15}")
        
        if local_info['schema_version'] or railway_info['schema_version']:
            local_ver = local_info['schema_version'] or 'N/A'
            railway_ver = railway_info['schema_version'] or 'N/A'
            self.log(f"{'Schema Version':<20} {local_ver:<15} {railway_ver:<15}")
        
        # Compare tables
        self.log("\nDetailed Table Comparison:")
        self.log("=" * 70)
        self.log(f"{'Table':<25} {'Local':<10} {'Railway':<10} {'Diff':<10} {'Status'}")
        self.log("=" * 70)
        
        all_tables = set(local_info['tables']) | set(railway_info['tables'])
        mismatches = []
        missing_local = []
        missing_railway = []
        
        for table in sorted(all_tables):
            local_count = local_info['table_counts'].get(table)
            railway_count = railway_info['table_counts'].get(table)
            
            if local_count is None:
                missing_local.append(table)
                status = "✗ MISSING LOCAL"
                diff = "N/A"
                railway_count = railway_count or 0
                local_count = "N/A"
            elif railway_count is None:
                missing_railway.append(table)
                status = "✗ MISSING RAILWAY"
                diff = "N/A"
                local_count = local_count or 0
                railway_count = "N/A"
            else:
                diff = railway_count - local_count
                if diff == 0:
                    status = "✓ MATCH"
                else:
                    status = "✗ MISMATCH"
                    mismatches.append(table)
                    diff = f"{diff:+d}"
            
            self.log(f"{table:<25} {str(local_count):<10} {str(railway_count):<10} {str(diff):<10} {status}")
        
        # Summary of issues
        issues = []
        if mismatches:
            issues.append(f"{len(mismatches)} table(s) with count mismatches")
        if missing_local:
            issues.append(f"{len(missing_local)} table(s) missing from local")
        if missing_railway:
            issues.append(f"{len(missing_railway)} table(s) missing from Railway")
        
        self.log("=" * 70)
        
        if issues:
            self.log("Issues Found:", "WARNING")
            for issue in issues:
                self.log(f"  - {issue}", "WARNING")
            
            if mismatches:
                self.log(f"\nTables with count mismatches: {', '.join(mismatches)}", "WARNING")
            if missing_local:
                self.log(f"Tables missing from local: {', '.join(missing_local)}", "WARNING")
            if missing_railway:
                self.log(f"Tables missing from Railway: {', '.join(missing_railway)}", "WARNING")
            
            self.log("\n✗ DATABASES ARE NOT IN SYNC", "ERROR")
            return False
        else:
            self.log("✓ ALL CHECKS PASSED - DATABASES ARE IN SYNC!", "SUCCESS")
            return True

def main():
    """Main function"""
    try:
        verifier = DatabaseVerifier()
        success = verifier.compare_databases()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 