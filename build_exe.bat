@echo off
setlocal
set "PYTHON=C:\py\.pixi\envs\default\python.exe"
set "PYTHONUTF8=1"

if not exist "%PYTHON%" goto missing
pushd "%~dp0"

echo Building dist\PinyinTrainer.exe ...
"%PYTHON%" -m PyInstaller --noconfirm --clean PinyinTrainer.spec
if errorlevel 1 goto failed

echo.
echo Done: %~dp0dist\PinyinTrainer.exe
popd
pause
exit /b 0

:failed
echo.
echo Build failed. See the output above.
popd
pause
exit /b 1

:missing
echo Python was not found at C:\py\.pixi\envs\default\python.exe
pause
exit /b 1
