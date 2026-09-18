@echo off
color 0C
title Stop JARVIS
echo Stopping JARVIS...
taskkill /FI "WINDOWTITLE eq JARVIS Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq JARVIS Frontend*" /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5500 " ^| findstr "LISTENING" 2^>nul') do taskkill /F /PID %%a >nul 2>&1
echo Done.
timeout /t 2 >nul