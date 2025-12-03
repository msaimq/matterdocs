@echo off
echo 🚀 Setting up Git for MatterDocs...
echo.

echo Step 1: Initialize Git repository
git init
echo ✅ Git repository initialized
echo.

echo Step 2: Add all files
git add .
echo ✅ Files staged for commit
echo.

echo Step 3: Create initial commit
git commit -m "Initial commit: MatterDocs legal document management system"
echo ✅ Initial commit created
echo.

echo Step 4: Create GitHub repository
echo Go to https://github.com/new and create a new repository named "matterdocs"
echo DO NOT initialize with README (we already have one)
echo.
pause

echo Step 5: Add remote origin
set /p GITHUB_URL="Enter your GitHub repository URL (e.g., https://github.com/username/matterdocs.git): "
git remote add origin %GITHUB_URL%
echo ✅ Remote origin added
echo.

echo Step 6: Push to GitHub
git branch -M main
git push -u origin main
echo ✅ Code pushed to GitHub
echo.


echo 🎉 Git setup complete!
echo Your code is now on GitHub and ready for Railway deployment.
echo.
echo Next steps:
echo 1. Go to railway.app
echo 2. Click "Deploy from GitHub"
echo 3. Select your matterdocs repository
echo 4. Railway will auto-deploy!
pause