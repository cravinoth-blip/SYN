@echo off
echo Starting Bronchiectasis Unlocked Questionnaire...
echo.
echo Open your browser at: http://localhost:5000
echo Admin panel at:       http://localhost:5000/admin
echo.
echo Press Ctrl+C to stop the server.
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe app.py
pause
