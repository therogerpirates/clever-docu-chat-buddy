
#!/usr/bin/env python3
"""
Script to create default users in the database.
Run this after setting up the database to create the initial users.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.create_users import create_default_users

if __name__ == "__main__":
    print("Creating default users...")
    create_default_users()
    print("Done!")
