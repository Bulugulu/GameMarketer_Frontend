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

# Database Configuration (adjust based on your database setup)
DB_HOST=your_database_host
DB_NAME=township_db
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_PORT=5432

# Streamlit Configuration (handled automatically by railway.toml)
PORT=8080
STREAMLIT_SERVER_PORT=8080
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

#### Optional Variables (if using Cohere reranking):
```bash
COHERE_API_KEY=your_cohere_api_key_here
```

### 3. Database Setup

If you need a PostgreSQL database, you can add one directly in Railway:

1. In your Railway project, click **+ New Service**
2. Select **PostgreSQL** from the database options
3. Railway will automatically create a database and provide connection details
4. Copy the connection variables to your app's environment variables

### 4. Deploy

1. Push your code to your connected repository
2. Railway will automatically build and deploy your app
3. The app will be available at the provided Railway URL

## Files Created for Deployment

- `Procfile`: Tells Railway how to run your Streamlit app
- `railway.toml`: Configuration file with build and deployment settings
- `requirements.txt`: Already exists with all necessary dependencies

## Configuration Details

### Procfile
```
web: streamlit run frontend_township.py --server.port=$PORT --server.address=0.0.0.0
```

### Key Settings in railway.toml
- Uses nixpacks builder for Python
- Sets up health check endpoint
- Configures Streamlit for production deployment
- Sets restart policy for reliability

## Troubleshooting

### Common Issues:

1. **App won't start**: Check that all environment variables are set correctly
2. **Database connection errors**: Verify DB_* variables match your database configuration
3. **OpenAI errors**: Ensure OPENAI_API_KEY is valid and has sufficient credits
4. **Port binding issues**: Railway automatically sets PORT variable, ensure your app uses it

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

1. **Database**: Consider using Railway's PostgreSQL add-on for production
2. **Environment Variables**: Never commit API keys to your repository
3. **Scaling**: Railway auto-scales based on usage
4. **Monitoring**: Set up notifications for deployment failures
5. **Backup**: Ensure your database has regular backups configured

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Community: [Railway Discord](https://railway.app/discord)
- For app-specific issues, check the logs in Railway dashboard 