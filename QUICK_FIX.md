# Quick Fix for PDF Upload Pipeline

## Issue
The `fix_pdf_pipeline.py` script failed because it couldn't create the `.env` file in the backend directory.

## Solution

### Step 1: Create the .env file manually
```bash
cd clever-docu-chat-buddy
python create_env.py
```

### Step 2: Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Test database connection
```bash
cd backend
python test_database.py
```

### Step 4: Test PDF processing
```bash
cd backend
python test_pdf_processing.py
```

### Step 5: Start the backend server
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Step 6: Test the full pipeline
In a new terminal:
```bash
cd clever-docu-chat-buddy
python test_pdf_pipeline.py
```

## What was fixed:

1. **Path Issues**: Fixed the script to use correct relative paths
2. **Environment Variables**: Created proper `.env` file in backend directory
3. **Dependencies**: Added missing packages to requirements.txt
4. **JWT Library**: Fixed JWT library imports in auth.py
5. **File Processing**: Fixed the upload endpoint to use proper processing functions

## Expected Results:

- Database connection should work
- PDF processing utilities should work
- File upload should work through the API
- Files should be stored in the database with embeddings

## Troubleshooting:

If you get database connection errors:
1. Check if the DATABASE_URL in the .env file is correct
2. Make sure the PostgreSQL database is accessible
3. Check if all required packages are installed

If you get PDF processing errors:
1. Make sure PyPDF2 and reportlab are installed
2. Check if the test PDF file exists
3. Verify Ollama is running for embeddings (optional)

If you get JWT errors:
1. Make sure python-jose is installed
2. Check if JWT_SECRET_KEY is set in .env 