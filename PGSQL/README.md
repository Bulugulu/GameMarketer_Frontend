# Railway Database Synchronization Scripts

This directory contains scripts to synchronize your local PostgreSQL database with Railway's hosted PostgreSQL service.

## Files Overview

- **`railway_db_sync.py`** - Main synchronization script (dump local → upload to Railway → verify)
- **`verify_sync.py`** - Standalone verification script to check database sync status
- **`sync_to_railway.bat`** - Windows batch script for easy execution

## Prerequisites

### 1. PostgreSQL Client Tools
You need `pg_dump` and `psql` installed and available in your PATH:

**Windows:**
- Download from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)
- Or install via [Chocolatey](https://chocolatey.org/): `choco install postgresql`

**macOS:**
```bash
brew install postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql-client
```

### 2. Python Dependencies
Install required packages (already in main requirements.txt):
```bash
pip install pg8000 python-dotenv
```

### 3. Environment Variables
Ensure your `.env.local` file contains:

**Local PostgreSQL Connection:**
The script needs these variables to connect to your local PostgreSQL instance:
```env
# Your project's environment variables (for LOCAL database)
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=your_database_name
PG_USER=your_username
PG_PASSWORD=your_password
# OR
DATABASE_PASSWORD=your_password
```

**Railway PostgreSQL Connection:**
Railway provides everything in a single URL (no separate variables needed):
```env
# This single URL contains username, password, host, port, and database name
DATABASE_PUBLIC_URL=postgresql://username:password@host:port/database
```

> **Note**: The `DATABASE_PUBLIC_URL` from Railway already contains all connection details (user, password, host, port, database). The separate `PG_*` variables (and `DATABASE_PASSWORD`) are only needed for your **local** PostgreSQL database.

## Usage

### Option 1: Windows Batch Script (Recommended for Windows)
```cmd
cd PGSQL
sync_to_railway.bat
```

The batch script will:
- Check all prerequisites
- Confirm before proceeding
- Run the synchronization
- Show results

### Option 2: Direct Python Execution
```bash
cd PGSQL
python railway_db_sync.py
```

### Option 3: Verification Only
To check if databases are in sync without doing a full transfer:
```bash
cd PGSQL
python verify_sync.py
```

## What the Sync Process Does

### 1. Connection Testing
- Tests connectivity to both local and Railway databases
- Validates credentials and network access

### 2. Database Dump
- Uses `pg_dump` to create a complete SQL dump of your local database
- Includes schema, data, and structure
- Uses `--clean` flag to remove existing objects before recreating

### 3. Upload to Railway
- Uses `psql` to execute the dump file against Railway database
- Replaces all existing data with local data

### 4. Verification
- Compares table counts between local and Railway
- Verifies all tables were transferred correctly
- Reports any discrepancies

## Output Example

```
============================================================
RAILWAY DATABASE SYNCHRONIZATION STARTED
============================================================
[2024-01-15 10:30:15] INFO: Local DB config loaded: user@localhost:5432/township_db
[2024-01-15 10:30:15] INFO: Railway DB config loaded: user@host:5432/railway_db
[2024-01-15 10:30:15] INFO: Testing database connections...
[2024-01-15 10:30:16] INFO: ✓ Local connection successful
[2024-01-15 10:30:17] INFO: ✓ Railway connection successful
[2024-01-15 10:30:17] INFO: Creating database dump: /tmp/township_db_dump_20240115_103017.sql
[2024-01-15 10:30:25] INFO: ✓ Database dump created successfully (15.23 MB)
[2024-01-15 10:30:25] INFO: Uploading dump to Railway database...
[2024-01-15 10:30:45] INFO: ✓ Database uploaded to Railway successfully
[2024-01-15 10:30:45] INFO: Verifying database synchronization...

Table count comparison:
==================================================
Table                     Local      Railway    Status
==================================================
feature_flow_step         1250       1250       ✓ MATCH
feature_updates           45         45         ✓ MATCH
features_game             892        892        ✓ MATCH
games                     12         12         ✓ MATCH
screen_feature_xref       2340       2340       ✓ MATCH
screenflow_xref           156        156        ✓ MATCH
screens                   445        445        ✓ MATCH
screenshot_feature_xref   5678       5678       ✓ MATCH
screenshot_video_xref     3421       3421       ✓ MATCH
screenshots               8932       8932       ✓ MATCH
taxon_features_xref       234        234        ✓ MATCH
taxon_screenshots_xref    1567       1567       ✓ MATCH
taxonomy                  89         89         ✓ MATCH
videos                    234        234        ✓ MATCH
==================================================
[2024-01-15 10:30:50] INFO: ✓ All table counts match - synchronization verified!
============================================================
✓ DATABASE SYNCHRONIZATION COMPLETED SUCCESSFULLY!
============================================================
```

## Troubleshooting

### Common Issues

**1. "pg_dump not found" or "psql not found"**
- Install PostgreSQL client tools
- Add PostgreSQL bin directory to your PATH

**2. "Connection failed"**
- Check your environment variables in `.env.local`
- Verify local PostgreSQL is running
- Test Railway connection URL manually

**3. "Permission denied"**
- Check database user permissions
- Ensure user has CREATE/DROP privileges for Railway sync

**4. "Table count mismatches"**
- Check if sync was interrupted
- Verify no other processes are modifying the databases
- Run verification script to see detailed differences

### Manual Connection Testing

Test local connection:
```bash
psql -h localhost -p 5432 -U your_user -d your_database
```

Test Railway connection:
```bash
psql "postgresql://username:password@host:port/database"
```

### Logs and Debugging

The scripts provide detailed logging. For additional debugging:

1. Check PostgreSQL logs on your local machine
2. Use Railway's database logs in their dashboard
3. Run verification script for detailed comparison

## Security Notes

- Never commit `.env.local` to version control
- Railway connection strings contain sensitive credentials
- Database dumps contain all your data - handle securely
- The sync process will **replace all data** in Railway database

## Database Schema

This sync process handles the complete Township game database schema including:
- Games and taxonomy reference tables
- Video tracking system
- Feature management and cross-references
- Screenshots with embeddings and video mappings
- Screen flow and navigation tracking

See `../Township_Database_Structure.md` for detailed schema documentation. 