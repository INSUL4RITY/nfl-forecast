@echo off
rem Run an nflcast command from ANY folder, e.g.
rem   & "C:\Users\Craig\NFL MODEL PROJECTIONS\nflcast.cmd" verify-claims
rem It switches to the project folder first, so relative paths such as .venv always resolve.
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m nflcast %*
exit /b %ERRORLEVEL%
