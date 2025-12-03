@echo off
echo 🔧 Fixing Railway deployment issues...
echo.

echo Adding fixes to git...
git add .
git commit -m "Fix: Railway deployment issues - improved Docker config and startup"
git push

echo ✅ Fixes pushed to GitHub
echo.
echo Railway will automatically redeploy with the fixes.
echo Check your Railway dashboard for the new deployment status.
pause