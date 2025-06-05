# Railway Deployment Guide for Township Feature Analyst

This guide will help you deploy your Township Feature Analyst Streamlit app to Railway.

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. Railway CLI installed (optional, but recommended)
3. Your OpenAI API key
4. Database credentials (if using external database)

## Deployment Steps

### 1. Connect Your Repository

1. Go to [railway.app](https://railway.app) and create a new project
2. Connect your GitHub repository containing this code
3. Railway will automatically detect it's a Python project

### 2. Set Environment Variables

In your Railway project dashboard, go to the **Variables** tab and add the following environment variables:

#### Required Variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Cohere API for reranking
COHERE_API_KEY=your_cohere_api_key_here
```

#### Database Configuration (Automatic):

The app automatically detects Railway environment and uses the correct database variables:

**Railway PostgreSQL** (automatically provided when you add PostgreSQL service):
- `PGHOST` - postgres.railway.internal
- `PGDATABASE` - railway
- `PGUSER` - postgres
- `PGPASSWORD` - (automatically generated)
- `PGPORT` - 5432

**Railway ChromaDB** (automatically provided when you add ChromaDB service):
- `CHROMA_PRIVATE_URL` - http://chroma.railway.internal
- `CHROMA_PUBLIC_URL` - https://your-chroma-instance.up.railway.app
- `CHROMA_SERVER_AUTHN_CREDENTIALS` - (if authentication is enabled)

**Local Development** uses different variable names:
- `PG_HOST`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_PORT`
- Local ChromaDB uses file-based storage

### 3. Database Setup

#### PostgreSQL Setup:

1. In your Railway project, click **+ New Service**
2. Select **PostgreSQL** from the database options
3. Railway will automatically create a database and provide connection variables
4. The app will automatically use these variables (no manual configuration needed)

#### ChromaDB Setup:

1. In your Railway project, click **+ New Service**
2. **Deploy ChromaDB Template**: Go to https://railway.com/deploy/kbvIRV and click "Deploy Now"
3. **Add to your project**: Choose your existing project when deploying the template
4. **Configure Service Variables**: Railway will automatically provide these variables:
   - `CHROMA_PRIVATE_URL` - Internal URL for service-to-service communication (recommended)
   - `CHROMA_PUBLIC_URL` - Public URL if needed for external access
   - `CHROMA_SERVER_AUTHN_CREDENTIALS` - Authentication token (automatically generated)
5. **Link to your app**: The app will automatically detect and use Railway ChromaDB

**Important**: Your app automatically uses `CHROMA_PRIVATE_URL` first, then falls back to `CHROMA_PUBLIC_URL`. The private URL is recommended for security and performance.

### 4. Deploy

1. Push your code to your connected repository
2. Railway will automatically build and deploy your app
3. The app will be available at the provided Railway URL

## Files Created for Deployment

- `Procfile`: Tells Railway how to run your Streamlit app
- `railway.toml`: Configuration file with build and deployment settings
- `requirements.txt`: Already exists with all necessary dependencies
- `utils/config.py`: Updated to automatically detect Railway environment

## Configuration Details

### Automatic Environment Detection

The app automatically detects whether it's running on Railway or locally by checking for Railway-specific environment variables. This means:

- **No manual configuration needed** - just deploy and it works
- **Same codebase** works for both local development and Railway
- **Automatic database switching** between local and Railway databases

### Procfile
```bash
web: streamlit run frontend_township.py --server.port=$PORT --server.address=0.0.0.0
```

### Key Settings in railway.toml
- Uses nixpacks builder for Python
- Sets up health check endpoint
- Configures Streamlit for production deployment
- Sets restart policy for reliability

## Troubleshooting

### Common Issues:

1. **App won't start**: Check that OPENAI_API_KEY is set
2. **Database connection errors**: Ensure PostgreSQL service is added to your Railway project
3. **ChromaDB errors**: Verify ChromaDB service is running and accessible
4. **OpenAI errors**: Ensure OPENAI_API_KEY is valid and has sufficient credits

### Logs
Check Railway deployment logs in the **Deployments** tab for detailed error messages.

### Health Check
Railway will monitor your app's health at `/_stcore/health` endpoint. If this fails repeatedly, Railway will restart the service.

## Post-Deployment

1. Test all functionality in the deployed app
2. Verify screenshot loading and database queries work correctly
3. Check that the vector search and chat features are operational
4. Monitor resource usage in Railway dashboard

## Production Considerations

1. **Database**: Railway's PostgreSQL and ChromaDB services are production-ready
2. **Environment Variables**: Never commit API keys to your repository
3. **Scaling**: Railway auto-scales based on usage
4. **Monitoring**: Set up notifications for deployment failures
5. **Backup**: Configure regular backups for your PostgreSQL database

## Environment Variable Reference

### Detected Automatically on Railway:
- `RAILWAY_ENVIRONMENT` - Indicates Railway environment
- `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` - Used for environment detection

### PostgreSQL (Railway provides these):
- `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGPORT`
- `DATABASE_URL`, `DATABASE_PUBLIC_URL`

### ChromaDB (Railway provides these):
- `CHROMA_PRIVATE_URL` - Internal URL for service-to-service communication
- `CHROMA_PUBLIC_URL` - Public URL if needed
- `CHROMA_SERVER_AUTHN_CREDENTIALS` - Authentication token if enabled

### Required by You:
- `OPENAI_API_KEY` - Your OpenAI API key
- `COHERE_API_KEY` - Optional, for enhanced search reranking

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Community: [Railway Discord](https://railway.app/discord)
- For app-specific issues, check the logs in Railway dashboard 