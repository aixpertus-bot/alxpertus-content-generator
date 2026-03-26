#!/usr/bin/env python3
"""
Alxpertus Content Generator - Starter Script
This script starts the API server with automatic scheduling
"""

import os
import sys

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║      🤖 Alxpertus Content Generator - v2.0                 ║
║      Automated Content Publishing System                  ║
╠═══════════════════════════════════════════════════════════╣
║  Features:                                                 ║
║  ✓ Generate content (English only)                        ║
║  ✓ Auto-generate images with FLUX                         ║
║  ✓ Schedule posts for auto-publishing                     ║
║  ✓ Publish to LinkedIn, X, Reddit                         ║
║  ✓ Track analytics (views, likes, comments, shares)        ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("\n🚀 Starting Alxpertus Content Generator...")
    
    # Add backend to path
    sys.path.insert(0, 'backend')
    
    # Import and start
    from api.main_en import app
    from scheduler import iniciar_scheduler
    
    # Start scheduler
    print("\n⏰ Starting automatic scheduler...")
    iniciar_scheduler()
    print("✅ Scheduler started")
    
    # Start server
    print("\n🌐 Starting API server on http://localhost:8000")
    print("📚 API Docs available at http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()