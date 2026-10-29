@echo off
setlocal
set "PYTHON=C:\py\.pixi\envs\default\python.exe"
set "PYTHONUTF8=1"

if not exist "%PYTHON%" goto missing
"%PYTHON%" "%~dp0main.py"
if errorlevel 1 pause
exit /b %errorlevel%

:missing
echo Python was not found at C:\py\.pixi\envs\default\python.exe
pause
exit /b 1
