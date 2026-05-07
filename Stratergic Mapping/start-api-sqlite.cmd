@echo off
cd /d "%~dp0apps\api"
set DATABASE_URL=sqlite:///./strategic_mapping_dev.db
set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8005
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8005 > ..\..\api.run.log 2>&1
