@echo off
echo 🚀 Deploying MatterDocs to Railway...
echo.

echo Step 1: Install Railway CLI
echo Run this command in a new terminal:
echo npm install -g @railway/cli
echo.
pause

echo Step 2: Login to Railway
echo Run this command:
echo railway login
echo.
pause

echo Step 3: Initialize and Deploy
echo Run these commands:
echo railway up
echo.
echo After deployment, Railway will give you a URL like:
echo https://your-app-name.up.railway.app
echo.
echo Step 4: Update manifest
echo Copy your Railway URL and run:
echo python update_manifest.py https://your-app-name.up.railway.app
echo.
pause

echo 🎉 Deployment process started!
echo Check Railway dashboard for deployment status.