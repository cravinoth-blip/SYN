@echo off
echo Starting Patient Journey App (local)...
echo.

echo [1/2] Starting Python backend on port 8000...
start "PJ Backend" cmd /k "cd /d "%~dp0backend" && uvicorn main:app --host 0.0.0.0 --port 8002 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Next.js frontend on port 3000...
start "PJ Frontend" cmd /k "cd /d "%~dp0app" && npm run dev"

echo.
echo App is starting...
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API docs: http://localhost:8000/docs
echo.
pause
