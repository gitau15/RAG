@echo off
REM Windows Deployment Script for RAG Platform
REM Usage: windows_deploy.bat [deploy|start|stop|status]

setlocal enabledelayedexpansion

echo ========================================
echo RAG Platform Windows Deployment
echo ========================================

REM Check if Docker is installed
echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows
    exit /b 1
)

REM Check if Docker Compose is installed
echo Checking Docker Compose installation...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose is not installed or not in PATH
    exit /b 1
)

REM Set project root directory
set PROJECT_ROOT=%~dp0..\..
cd /d "%PROJECT_ROOT%"

REM Parse command line arguments
set ACTION=%1
if "%ACTION%"=="" set ACTION=deploy

echo Action: %ACTION%
echo Project Root: %PROJECT_ROOT%
echo.

REM Execute requested action
if "%ACTION%"=="deploy" (
    call :deploy_platform
) else if "%ACTION%"=="start" (
    call :start_services
) else if "%ACTION%"=="stop" (
    call :stop_services
) else if "%ACTION%"=="status" (
    call :show_status
) else if "%ACTION%"=="logs" (
    call :show_logs
) else (
    echo Unknown action: %ACTION%
    echo Usage: %0 [deploy^|start^|stop^|status^|logs]
    exit /b 1
)

exit /b 0

:deploy_platform
echo Deploying RAG Platform...
echo.

REM Setup directories
echo Creating required directories...
mkdir "local_storage" 2>nul
mkdir "local_storage\chroma" 2>nul
mkdir "local_storage\ollama" 2>nul
mkdir "local_storage\logs" 2>nul
mkdir "local_storage\backups" 2>nul

REM Create environment file if it doesn't exist
if not exist "backend\.env" (
    echo Creating environment file...
    echo ENVIRONMENT=production > "backend\.env"
    echo DEBUG=False >> "backend\.env"
    echo CHROMA_DB_PATH=/home/app/chroma_db >> "backend\.env"
    echo OLLAMA_HOST=http://ollama:11434 >> "backend\.env"
    echo OLLAMA_MODEL=mistral:7b >> "backend\.env"
    echo SECRET_KEY=your-secret-key-change-in-production >> "backend\.env"
)

REM Build and start services
echo Building Docker images...
docker-compose build
if %errorlevel% neq 0 (
    echo ERROR: Docker build failed
    exit /b 1
)

echo Starting services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start services
    exit /b 1
)

echo.
echo Waiting for services to start...
timeout /t 30 /nobreak >nul

echo.
echo Checking service status...
docker-compose ps

echo.
echo Deployment completed!
echo Access the platform at:
echo   Frontend: http://localhost:3000
echo   Backend API: http://localhost:8000
echo   API Documentation: http://localhost:8000/docs
goto :eof

:start_services
echo Starting RAG Platform services...
docker-compose up -d
if %errorlevel% equ 0 (
    echo Services started successfully
) else (
    echo ERROR: Failed to start services
)
goto :eof

:stop_services
echo Stopping RAG Platform services...
docker-compose down
if %errorlevel% equ 0 (
    echo Services stopped successfully
) else (
    echo ERROR: Failed to stop services
)
goto :eof

:show_status
echo RAG Platform Service Status:
docker-compose ps
goto :eof

:show_logs
echo Showing RAG Platform logs:
docker-compose logs -f
goto :eof