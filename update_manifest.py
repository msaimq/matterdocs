#!/usr/bin/env python3
"""Update manifest URLs for different environments."""

import sys
from pathlib import Path

def update_manifest(base_url: str):
    """Update manifest file with new base URL."""
    manifest_path = Path("matterdocs-outlook-manifest.xml")
    
    if not manifest_path.exists():
        print("Manifest file not found!")
        return False
    
    content = manifest_path.read_text()
    
    # Replace all localhost:8000 references
    content = content.replace("https://localhost:8000", base_url)
    content = content.replace("http://localhost:8000", base_url)
    
    manifest_path.write_text(content)
    print(f"✅ Updated manifest URLs to: {base_url}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_manifest.py <base_url>")
        print("Example: python update_manifest.py https://abc123.ngrok.io")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    update_manifest(base_url)