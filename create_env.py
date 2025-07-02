#!/usr/bin/env python3
"""
Create .env file in backend directory
"""

import os
import shutil
from pathlib import Path

def create_env_file():
    """Create .env file in backend directory"""
    
    # Get current directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Check if we're in the right directory
    if not (current_dir / "backend").exists():
        print("❌ Backend directory not found. Please run this script from the clever-docu-chat-buddy directory.")
        return False
    
    # Source and destination paths
    env_source = current_dir / "env"
    env_dest = current_dir / "backend" / ".env"
    
    print(f"📋 Source env file: {env_source}")
    print(f"📋 Destination .env file: {env_dest}")
    
    if env_source.exists():
        # Copy the env file
        shutil.copy2(env_source, env_dest)
        print(f"✅ Successfully copied {env_source} to {env_dest}")
        
        # Add additional environment variables if needed
        with open(env_dest, 'a') as f:
            f.write("\n# Additional environment variables\n")
            f.write("EMBEDDING_RETRY_DELAY=5\n")
            f.write("EMBEDDING_MAX_RETRIES=3\n")
            f.write("JWT_SECRET_KEY=your-secret-key-change-this-in-production\n")
            f.write("ACCESS_TOKEN_EXPIRE_MINUTES=30\n")
        
        print("✅ Added additional environment variables")
        return True
    else:
        print(f"❌ Source env file not found: {env_source}")
        return False

if __name__ == "__main__":
    success = create_env_file()
    if success:
        print("\n🎉 .env file created successfully!")
    else:
        print("\n💥 Failed to create .env file!") 