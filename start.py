#!/usr/bin/env python3
"""Production startup script for Railway deployment."""

import os
import uvicorn
from pathlib import Path

def main():
    """Start the application with proper configuration."""
    
    # Ensure required directories exist
    storage_dir = Path(os.getenv("STORAGE_ROOT", "storage"))
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Get port from environment (Railway sets this)
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Starting MatterDocs on port {port}")
    print(f"📁 Storage directory: {storage_dir}")
    
    # Start uvicorn server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        access_log=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()