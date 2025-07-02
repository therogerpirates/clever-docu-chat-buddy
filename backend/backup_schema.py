import subprocess
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load .env file from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'env'))

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL not found in env file')

# Parse the DATABASE_URL
parsed = urlparse(DATABASE_URL)
DB_USER = parsed.username
DB_PASSWORD = parsed.password
DB_HOST = parsed.hostname
DB_PORT = str(parsed.port or 5432)
DB_NAME = parsed.path.lstrip('/')

# Output file for schema backup
OUTPUT_FILE = 'db_schema_backup.sql'

# Set the PGPASSWORD environment variable for non-interactive password passing
os.environ['PGPASSWORD'] = DB_PASSWORD

# Construct the pg_dump command
cmd = [
    'pg_dump',
    '--host', DB_HOST,
    '--port', DB_PORT,
    '--username', DB_USER,
    '--schema-only',
    '--no-owner',
    '--file', OUTPUT_FILE,
    DB_NAME
]

try:
    print(f"Backing up schema of database '{DB_NAME}' to '{OUTPUT_FILE}'...")
    subprocess.run(cmd, check=True)
    print("Backup completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error during backup: {e}")
finally:
    # Clean up the password from environment
    del os.environ['PGPASSWORD'] 