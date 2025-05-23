# Township Feature Analyst

A Streamlit application for analyzing Township game features using PostgreSQL database and OpenAI's GPT models.

## Features

- Interactive chatbot interface for querying Township game data
- SQL query execution against PostgreSQL database
- Screenshot retrieval and display functionality
- Integration with OpenAI's GPT models for natural language processing

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env.local` file with your configuration:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   DB_HOST=localhost
   DB_NAME=township_db
   DB_USER=postgres
   DB_PASSWORD=your_password_here
   DB_PORT=5432
   ```

3. Run the application:
   ```bash
   streamlit run frontend_township.py
   ```

## Git LFS Configuration

This repository uses Git LFS (Large File Storage) for files larger than 100MB. Currently tracked file types:

- `*.pdf` - PDF documents
- `*.zip` - ZIP archives  
- `*.tar.gz` - Compressed archives

### Adding Large Files

If you need to add files larger than 100MB to the repository:

1. First, track the file type with Git LFS:
   ```bash
   git lfs track "*.your_extension"
   ```

2. Add and commit the `.gitattributes` file:
   ```bash
   git add .gitattributes
   git commit -m "Track large files with LFS"
   ```

3. Then add your large files:
   ```bash
   git add your_large_file.ext
   git commit -m "Add large file"
   ```

### Note on Image Files

Image files (PNG, JPG, etc.) and video files are completely ignored by Git and not tracked in the repository. This includes the `screenshots/` directory which contains the application's screenshot data.

## File Structure

- `frontend_township.py` - Main Streamlit application
- `database_tool.py` - Database connection and query utilities
- `requirements.txt` - Python dependencies
- `Township_Database_Structure.md` - Database schema documentation
- `screenshots/` - Screenshot files (ignored by Git) 