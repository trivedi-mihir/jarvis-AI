@echo off
setlocal
title JARVIS Launcher
color 0B
mode con: cols=84 lines=46
cls

cd /d "%~dp0"
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "FE=%ROOT%\frontend"
set "BE=%ROOT%\backend"
set "LOG=%ROOT%\jarvis_launcher.log"

echo JARVIS Launcher Log - %DATE% %TIME% > "%LOG%"

echo.
echo  ============================================================
echo                 J A R V I S   A G E N T
echo  ============================================================
echo.
echo   Root folder : %ROOT%
echo.

:: ============================================================
:: STEP 1 — FIND PYTHON
:: ============================================================
echo  [1/7] Checking Python...

set "PY="
where py >nul 2>&1
if %errorlevel%==0 set "PY=py"

if not defined PY (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY=python"
)

if not defined PY (
    echo.
    echo   [FAIL] Python is NOT installed.
    echo.
    echo   Install Python 3.10+ from:
    echo       https://www.python.org/downloads/
    echo.
    echo   During install check:  [X] Add Python to PATH
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PY% --version 2^>^&1') do set "PYV=%%v"
echo        Found Python %PYV%  (using: %PY%)
echo.

:: ============================================================
:: STEP 2 — VERIFY ESSENTIAL FILES
:: ============================================================
echo  [2/7] Verifying essential files...

set "MISS=0"

if not exist "%FE%\index.html"        ( echo   [MISSING] frontend\index.html & set MISS=1 )
if not exist "%FE%\style.css"         ( echo   [MISSING] frontend\style.css & set MISS=1 )
if not exist "%FE%\script.js"         ( echo   [MISSING] frontend\script.js & set MISS=1 )

if not exist "%BE%\main.py"           ( echo   [MISSING] backend\main.py & set MISS=1 )
if not exist "%BE%\config.py"         ( echo   [MISSING] backend\config.py & set MISS=1 )
if not exist "%BE%\agent.py"          ( echo   [MISSING] backend\agent.py & set MISS=1 )

if not exist "%BE%\tools\__init__.py" ( echo   [MISSING] backend\tools\__init__.py & set MISS=1 )
if not exist "%BE%\tools\registry.py" ( echo   [MISSING] backend\tools\registry.py & set MISS=1 )

if "%MISS%"=="1" (
    echo.
    echo   [FAIL] Essential files are missing. Fix them and retry.
    echo.
    pause
    exit /b 1
)

echo        All essential files present.
echo.

:: ============================================================
:: STEP 3 — UPGRADE PIP
:: ============================================================
echo  [3/7] Upgrading pip (silent)...
%PY% -m pip install --upgrade pip --quiet --disable-pip-version-check >>"%LOG%" 2>&1
echo        Done.
echo.

:: ============================================================
:: STEP 4 — INSTALL MISSING DEPENDENCIES
:: ============================================================
echo  [4/7] Checking Python dependencies...

set "NEED="

%PY% -c "import fastapi"        >nul 2>&1 || set NEED=1
%PY% -c "import uvicorn"        >nul 2>&1 || set NEED=1
%PY% -c "import pydantic"       >nul 2>&1 || set NEED=1
%PY% -c "import psutil"         >nul 2>&1 || set NEED=1
%PY% -c "import pyperclip"      >nul 2>&1 || set NEED=1
%PY% -c "import requests"       >nul 2>&1 || set NEED=1
%PY% -c "import pyautogui"      >nul 2>&1 || set NEED=1
%PY% -c "from PIL import Image" >nul 2>&1 || set NEED=1

if not defined NEED (
    echo        All dependencies already installed.
) else (
    echo        Installing missing packages - please wait 1-3 minutes...
    echo.
    %PY% -m pip install --disable-pip-version-check ^
        fastapi ^
        "uvicorn[standard]" ^
        pydantic ^
        psutil ^
        pyperclip ^
        requests ^
        pyautogui ^
        Pillow >>"%LOG%" 2>&1

    if errorlevel 1 (
        echo.
        echo   [FAIL] Failed to install Python packages.
        echo          Check your internet connection.
        echo          See log: %LOG%
        echo.
        pause
        exit /b 1
    )
    echo        Dependencies installed.
)
echo.

:: ============================================================
:: STEP 5 — TEST BACKEND IMPORT
:: ============================================================
echo  [5/7] Testing backend import...

pushd "%BE%"
%PY% -c "import main" >nul 2>>"%LOG%"
set "IMP=%errorlevel%"
popd

if not "%IMP%"=="0" (
    echo.
    echo   [FAIL] Backend import failed.
    echo          Open this file to see the error:
    echo          %LOG%
    echo.
    echo   Most common causes:
    echo     - a file in backend\tools\ is missing
    echo     - a syntax error in one of the Python files
    echo.
    pause
    exit /b 1
)

echo        Backend imports OK.
echo.

:: ============================================================
:: STEP 6 — FREE PORTS 8000 AND 5500
:: ============================================================
echo  [6/7] Freeing ports 8000 and 5500...

call :KillPort 8000
call :KillPort 5500

echo        Ports are ready.
echo.

:: ============================================================
:: STEP 7 — START SERVERS + OPEN BROWSER
:: ============================================================
echo  [7/7] Starting servers...

start "JARVIS Backend" cmd /k "cd /d "%BE%" && title JARVIS Backend && echo. && echo  JARVIS SYSTEM BRIDGE - keep this window open && echo. && %PY% main.py"

echo        Waiting for backend to boot...
timeout /t 5 /nobreak >nul

start "JARVIS Frontend" cmd /k "cd /d "%FE%" && title JARVIS Frontend && echo. && echo  JARVIS WEBSITE SERVER - keep this window open && echo. && %PY% -m http.server 5500 --bind 127.0.0.1"

echo        Waiting for website to boot...
timeout /t 4 /nobreak >nul

echo        Opening browser...
start "" "http://127.0.0.1:5500"

echo.
echo  ============================================================
echo                    JARVIS IS ONLINE
echo  ============================================================
echo.
echo    Website:       http://127.0.0.1:5500
echo    Backend:       http://127.0.0.1:8000
echo.
echo    Two new windows opened:
echo      - JARVIS Backend   (Python tool server)
echo      - JARVIS Frontend  (Website server)
echo.
echo    In the browser:
echo      1. Click the gear icon (top-right)
echo      2. Paste your OpenRouter API key
echo         (get free at https://openrouter.ai/keys)
echo      3. Click TEST CONNECTION
echo.
echo    Try commands:
echo      "What time is it?"
echo      "What is my RAM?"
echo      "Open Chrome"
echo      "Create a folder called Test on my Desktop"
echo      "Take a screenshot"
echo.
echo    To stop JARVIS: run STOP-JARVIS.cmd
echo  ============================================================
echo.
echo    Log saved to: %LOG%
echo.
pause
exit /b 0

:: ============================================================
:: HELPER: Kill whatever is using the given port
:: ============================================================
:KillPort
setlocal
set "P=%~1"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":!P! " 2^>nul ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
endlocal
exit /b 0