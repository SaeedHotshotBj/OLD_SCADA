@echo off
setlocal EnableExtensions

REM ============================================================
REM OLD SCADA - ONE CLICK DEPLOY
REM ============================================================
REM This file uploads the current project folder to the server,
REM runs deploy.sh, restarts the SCADA service, then reboots the server.
REM ============================================================

set "SERVER_IP=77.104.95.230"
set "SERVER_USER=root"
set "SERVER_PASS=I4Ql50K7KKIkZnhG"
set "SERVER_DIR=/var/www/global"
set "TOOLS_DIR=%~dp0tools"
set "PSCP=%TOOLS_DIR%\pscp.exe"
set "PLINK=%TOOLS_DIR%\plink.exe"

if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

REM ------------------------------------------------------------
REM Download PuTTY PSCP/PLINK automatically if they are missing.
REM Official PuTTY distribution.
REM ------------------------------------------------------------
if not exist "%PSCP%" (
    echo Downloading PSCP...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://the.earth.li/~sgtatham/putty/0.85/w64/pscp.exe' -OutFile '%PSCP%'"
    if errorlevel 1 goto DOWNLOAD_ERROR
)

if not exist "%PLINK%" (
    echo Downloading PLINK...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://the.earth.li/~sgtatham/putty/0.85/w64/plink.exe' -OutFile '%PLINK%'"
    if errorlevel 1 goto DOWNLOAD_ERROR
)

if not exist "%PSCP%" goto DOWNLOAD_ERROR
if not exist "%PLINK%" goto DOWNLOAD_ERROR

REM ------------------------------------------------------------
REM Upload the project files from this folder.
REM ------------------------------------------------------------
echo.
echo ==========================================
echo Uploading OLD SCADA files...
echo ==========================================
echo.

"%PSCP%" -r -pw "%SERVER_PASS%" "%~dp0*" "%SERVER_USER%@%SERVER_IP%:%SERVER_DIR%/"
if errorlevel 1 goto UPLOAD_ERROR

echo.
echo Upload successful.
echo.

REM ------------------------------------------------------------
REM Run the existing server deployment script.
REM It installs dependencies, creates the DB and systemd service,
REM and starts old-scada.service.
REM Then schedule a full server reboot.
REM ------------------------------------------------------------
echo ==========================================
echo Deploying on server...
echo ==========================================
echo.

"%PLINK%" -ssh -pw "%SERVER_PASS%" "%SERVER_USER%@%SERVER_IP%" "cd %SERVER_DIR% && chmod +x deploy.sh && bash deploy.sh && echo 'DEPLOY_OK' && nohup sh -c 'sleep 5; reboot' >/dev/null 2>&1 &"

if errorlevel 1 goto REMOTE_ERROR

echo.
echo ==========================================
echo DEPLOY COMMAND COMPLETED
necho The server will reboot in a few seconds.
echo ==========================================
echo.
pause
exit /b 0

:DOWNLOAD_ERROR
echo.
echo ERROR: Could not download PSCP/PLINK.
echo Check your internet connection and try again.
pause
exit /b 1

:UPLOAD_ERROR
echo.
echo ERROR: Upload failed.
echo Check the server IP, SSH port and password.
pause
exit /b 1

:REMOTE_ERROR
echo.
echo ERROR: Remote deployment failed.
echo Check the SSH output above.
pause
exit /b 1
