@echo off
echo 🚀 Setting up Railway with PostgreSQL...
echo.

echo Step 1: Add PostgreSQL to your Railway project
echo 1. Go to your Railway dashboard
echo 2. Click "New" → "Database" → "Add PostgreSQL"
echo 3. Railway will provide a DATABASE_URL automatically
echo.
pause

echo Step 2: Update and deploy
git add .
git commit -m "Fix: Add PostgreSQL support for Railway deployment"
git push

echo ✅ Code updated with PostgreSQL support
echo.
echo Railway will now:
echo - Use PostgreSQL database (persistent)
echo - Auto-deploy with the new configuration
echo.
echo Note: File uploads are still temporary on Railway
echo For production, consider adding cloud storage (AWS S3, etc.)
pause