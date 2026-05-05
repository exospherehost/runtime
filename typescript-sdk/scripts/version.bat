@echo off
REM Version management script for Windows
REM 
REM Usage:
REM   scripts\version.bat beta    # Create beta version (0.1.0b1)
REM   scripts\version.bat patch   # Create patch version (0.1.1)
REM   scripts\version.bat minor   # Create minor version (0.2.0)
REM   scripts\version.bat major   # Create major version (1.0.0)

if "%1"=="" (
    echo.
    echo Version Management Script for ExosphereHost TypeScript SDK
    echo.
    echo Usage:
    echo   scripts\version.bat ^<type^>
    echo.
    echo Types:
    echo   beta    Create a beta version (e.g., 0.1.0b1, 0.1.0b2)
    echo   patch   Create a patch version (e.g., 0.1.0 -^> 0.1.1)
    echo   minor   Create a minor version (e.g., 0.1.0 -^> 0.2.0)
    echo   major   Create a major version (e.g., 0.1.0 -^> 1.0.0)
    echo.
    echo Examples:
    echo   scripts\version.bat beta    # 0.1.0 -^> 0.1.0b1
    echo   scripts\version.bat patch   # 0.1.0b1 -^> 0.1.0
    echo   scripts\version.bat minor   # 0.1.0 -^> 0.2.0
    echo   scripts\version.bat major   # 0.1.0 -^> 1.0.0
    echo.
    goto :eof
)

node scripts/version.js %1
