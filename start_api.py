#!/usr/bin/env python3
"""
Script to start the API server with clean module loading
"""

import os
import sys
import subprocess
import shutil

def clear_cache():
    """Clear all Python cache"""
    print("🧹 Clearing Python cache...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                cache_path = os.path.join(root, d)
                print(f"  Removing {cache_path}")
                shutil.rmtree(cache_path, ignore_errors=True)
    
    # Remove .pyc files
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.pyc'):
                pyc_path = os.path.join(root, f)
                print(f"  Removing {pyc_path}")
                os.remove(pyc_path)

def start_server():
    """Start the API server"""
    print("\n🚀 Starting API server...")
    
    # Add backend to path
    sys.path.insert(0, 'backend')
    
    # Import and run
    from api.main import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    clear_cache()
    start_server()
