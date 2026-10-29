@echo off
setlocal
set "PYTHONW=C:\py\.pixi\envs\default\pythonw.exe"
set "PYTHON=C:\py\.pixi\envs\default\python.exe"
set "PYTHONUTF8=1"

if not exist "%PYTHONW%" goto try_console
start "" "%PYTHONW%" "%~dp0main.py"
exit /b 0

:try_console
if not exist "%PYTHON%" goto missing
"%PYTHON%" "%~dp0main.py"
exit /b %errorlevel%

:missing
echo Python was not found at C:\py\.pixi\envs\default\python.exe
echo Please check the C:\py environment.
pause
exit /b 1
