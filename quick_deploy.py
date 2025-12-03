#!/usr/bin/env python3
"""Quick deployment to Railway (free tier)."""

import subprocess
import sys
import json

def deploy_to_railway():
    """Deploy to Railway for quick HTTPS hosting."""
    
    print("🚀 Quick Deploy to Railway (Free Tier)")
    print("1. Install Railway CLI: npm install -g @railway/cli")
    print("2. Login: railway login")
    print("3. Deploy: railway up")
    print()
    
    # Create railway.json
    railway_config = {
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
            "healthcheckPath": "/",
            "healthcheckTimeout": 100,
            "restartPolicyType": "ON_FAILURE"
        }
    }
    
    with open("railway.json", "w") as f:
        json.dump(railway_config, f, indent=2)
    
    print("✅ Created railway.json")
    
    # Create Procfile for Railway
    with open("Procfile", "w") as f:
        f.write("web: uvicorn main:app --host 0.0.0.0 --port $PORT")
    
    print("✅ Created Procfile")
    
    print("\n📋 Next steps:")
    print("1. Run: npm install -g @railway/cli")
    print("2. Run: railway login")
    print("3. Run: railway up")
    print("4. Copy the deployment URL")
    print("5. Run: python update_manifest.py <your-railway-url>")

def deploy_to_render():
    """Deploy to Render (free tier)."""
    
    print("🚀 Quick Deploy to Render (Free Tier)")
    
    # Create render.yaml
    render_config = {
        "services": [
            {
                "type": "web",
                "name": "matterdocs",
                "env": "python",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                "envVars": [
                    {
                        "key": "DATABASE_URL",
                        "value": "sqlite:///app/matterdocs.db"
                    },
                    {
                        "key": "STORAGE_ROOT", 
                        "value": "/app/storage"
                    }
                ]
            }
        ]
    }
    
    with open("render.yaml", "w") as f:
        import yaml
        yaml.dump(render_config, f, default_flow_style=False)
    
    print("✅ Created render.yaml")
    print("\n📋 Next steps:")
    print("1. Push code to GitHub")
    print("2. Go to https://render.com")
    print("3. Connect your GitHub repo")
    print("4. Deploy as Web Service")
    print("5. Copy the deployment URL")
    print("6. Run: python update_manifest.py <your-render-url>")

if __name__ == "__main__":
    print("Choose deployment option:")
    print("1. Railway (recommended)")
    print("2. Render")
    print("3. AWS (requires AWS CLI setup)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        deploy_to_railway()
    elif choice == "2":
        deploy_to_render()
    elif choice == "3":
        print("Run: python deploy_apprunner.py")
    else:
        print("Invalid choice")