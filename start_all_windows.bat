@echo off
REM Windows Batch script to start all services in separate windows
REM Eco-Friendly Community - Full Stack Application

echo ========================================
echo Eco-Friendly Community - Starting All Services
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"
set PROJECT_ROOT=%~dp0
set BACKEND_DIR=%PROJECT_ROOT%backend

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

REM Set environment variables
set MODEL_API_URL=http://127.0.0.1:7000/analyze_post
set FASTAPI_ANALYZE_URL=http://127.0.0.1:8000/analyze
set FLASK_PORT=7000
set PORT=5000
set DB_HOST=localhost
set DB_USER=root
set DB_NAME=green_points

REM Determine Python executable
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe
    echo Using virtual environment Python: %PYTHON_EXE%
) else (
    set PYTHON_EXE=python
    echo Using system Python
)

echo.
echo Starting services in separate windows...
echo.

REM 1. Start FastAPI AI Service (port 8000)
echo [1/5] Starting FastAPI AI Service on port 8000...
start "FastAPI AI Service (8000)" cmd /k "cd /d %BACKEND_DIR% && %PYTHON_EXE% -m uvicorn model_api:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul

REM 2. Start Flask Database API (port 7000)
echo [2/5] Starting Flask Database API on port 7000...
start "Flask Database API (7000)" cmd /k "cd /d %BACKEND_DIR% && %PYTHON_EXE% flask_app.py"
timeout /t 3 /nobreak >nul

REM 3. Start Node.js/Express Backend (port 5000)
echo [3/5] Starting Node.js Backend on port 5000...
if not exist "%BACKEND_DIR%\node_modules" (
    echo Installing backend dependencies...
    cd /d %BACKEND_DIR%
    call npm install
    cd /d %PROJECT_ROOT%
)
start "Node.js Backend (5000)" cmd /k "cd /d %BACKEND_DIR% && npm start"
timeout /t 3 /nobreak >nul

REM 4. Start Streamlit ML UI (port 8501) - Integrated version for frontend
echo [4/5] Starting Streamlit ML UI on port 8501...
start "Streamlit ML UI (8501)" cmd /k "cd /d %BACKEND_DIR% && %PYTHON_EXE% -m streamlit run streamlit_integrated.py --server.port 8501 --server.headless true"
timeout /t 3 /nobreak >nul

REM 5. Start Frontend Vite (port 3000)
echo [5/5] Starting Vite Frontend on port 3000...
if not exist "%PROJECT_ROOT%node_modules" (
    echo Installing frontend dependencies...
    cd /d %PROJECT_ROOT%
    call npm install
)
start "Vite Frontend (3000)" cmd /k "cd /d %PROJECT_ROOT% && npm run dev"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo Services available at:
echo   - Frontend (Vite):     http://localhost:3000
echo   - Streamlit UI:        http://localhost:8501
echo   - Node.js Backend:     http://127.0.0.1:5000
echo   - Flask API:           http://127.0.0.1:7000
echo   - FastAPI (AI):        http://127.0.0.1:8000
echo   - FastAPI Docs:        http://127.0.0.1:8000/docs
echo.
echo Each service is running in a separate window.
echo Close the windows to stop individual services.
echo.
echo Waiting 10 seconds before opening browsers...
timeout /t 10 /nobreak >nul

REM Open browsers
start http://localhost:3000
timeout /t 2 /nobreak >nul
start http://localhost:8501

echo.
echo Browsers opened! You can now use the application.
echo.
echo Press any key to exit this window (services will continue running)...
pause >nul

