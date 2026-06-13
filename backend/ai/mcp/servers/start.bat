@echo off
REM MCP Servers - Startup and Management Script (Windows)
REM Usage: start.bat [command]

setlocal enabledelayedexpansion

REM Color codes (using choice command for colors)
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set BLUE=[94m
set NC=[0m

REM Check if command line argument is provided
if "%1"=="" (
    call :usage
    exit /b 0
)

REM Check Docker installation
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Docker is not installed or not in PATH
    exit /b 1
)

REM Execute command
if "%1"=="setup" (
    call :setup
) else if "%1"=="build" (
    call :build
) else if "%1"=="start" (
    call :start
) else if "%1"=="stop" (
    call :stop
) else if "%1"=="restart" (
    call :restart
) else if "%1"=="status" (
    call :status
) else if "%1"=="logs" (
    call :logs %2
) else if "%1"=="health" (
    call :health
) else if "%1"=="shell" (
    call :shell %2
) else if "%1"=="clean" (
    call :clean
) else if "%1"=="help" (
    call :usage
) else (
    echo Unknown command: %1
    echo.
    call :usage
    exit /b 1
)

exit /b 0

REM ============== FUNCTIONS ==============

:setup
echo.
echo ========================================
echo Setting up MCP Servers
echo ========================================
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please update .env with your credentials
) else (
    echo .env already exists
)
if not exist "secrets" mkdir secrets
if not exist "logs" mkdir logs
echo Setup complete
goto :eof

:build
echo.
echo ========================================
echo Building Docker Images
echo ========================================
docker-compose build --no-cache
echo Build complete
goto :eof

:start
echo.
echo ========================================
echo Starting MCP Servers
echo ========================================
docker-compose up -d
echo Waiting for services to be ready...
timeout /t 5 /nobreak
call :status
goto :eof

:stop
echo.
echo ========================================
echo Stopping MCP Servers
echo ========================================
docker-compose down
echo Services stopped
goto :eof

:restart
echo.
echo ========================================
echo Restarting MCP Servers
echo ========================================
docker-compose restart
timeout /t 3 /nobreak
call :status
goto :eof

:status
echo.
echo ========================================
echo Service Status
echo ========================================
docker-compose ps
echo.
echo Service URLs:
echo   SQL Server:      http://localhost:3001
echo   Google Drive:    http://localhost:3002
echo   SharePoint:      http://localhost:3003
echo   Dropbox:         http://localhost:3004
echo.
goto :eof

:logs
if "%~1"=="" (
    docker-compose logs -f
) else (
    docker-compose logs -f %~1
)
goto :eof

:health
echo.
echo ========================================
echo Health Check
echo ========================================
echo Checking SQL Server...
docker-compose exec sql-server python -c "print('OK')" >nul 2>&1
if errorlevel 1 (
    echo SQL Server unreachable
) else (
    echo SQL Server OK
)

echo Checking Google Drive Server...
docker-compose exec google-drive-server python -c "print('OK')" >nul 2>&1
if errorlevel 1 (
    echo Google Drive Server unreachable
) else (
    echo Google Drive Server OK
)

echo Checking SharePoint Server...
docker-compose exec sharepoint-server python -c "print('OK')" >nul 2>&1
if errorlevel 1 (
    echo SharePoint Server unreachable
) else (
    echo SharePoint Server OK
)

echo Checking Dropbox Server...
docker-compose exec dropbox-server python -c "print('OK')" >nul 2>&1
if errorlevel 1 (
    echo Dropbox Server unreachable
) else (
    echo Dropbox Server OK
)
goto :eof

:shell
if "%~1"=="" (
    echo Service not specified
    echo Usage: start.bat shell [sql-server^|google-drive-server^|sharepoint-server]
    exit /b 1
)
docker-compose exec %~1 cmd
goto :eof

:clean
echo.
echo ========================================
echo Cleaning Up
echo ========================================
echo Stopping containers...
docker-compose down -v
echo Cleanup complete
goto :eof

:usage
echo.
echo MCP Servers Management Script (Windows)
echo.
echo Usage: start.bat [command]
echo.
echo Commands:
echo   setup              Setup environment
echo   build              Build Docker images
echo   start              Start all services
echo   stop               Stop all services
echo   restart            Restart all services
echo   status             Show service status
echo   logs [service]     View logs (optional: service name)
echo   health             Run health checks
echo   shell [service]    Open shell in service container
echo   clean              Clean up and remove containers
echo   help               Show this help message
echo.
echo Examples:
echo   start.bat setup
echo   start.bat build
echo   start.bat start
echo   start.bat logs sql-server
echo   start.bat logs dropbox-server
echo   start.bat shell google-drive-server
echo.
goto :eof

endlocal
