@echo off
title VEDAI - Git Push

echo.
echo ========================================
echo          VEDAI GIT PUSH
echo ========================================
echo.

REM Check if Git is installed
git --version >nul 2>&1

if errorlevel 1 (
    echo ERROR: Git is not installed or not available in PATH.
    echo.
    pause
    exit /b 1
)

REM Check if this is a Git repository
if not exist ".git" (
    echo Git repository not found.
    echo Initializing Git repository...
    echo.

    git init

    if errorlevel 1 (
        echo ERROR: Could not initialize Git.
        pause
        exit /b 1
    )
)

echo.
echo ----------------------------------------
echo Adding files...
echo ----------------------------------------
git add .

if errorlevel 1 (
    echo ERROR: git add failed.
    pause
    exit /b 1
)

echo.
echo ----------------------------------------
echo Current Git status
echo ----------------------------------------
git status

echo.
echo ----------------------------------------
echo Creating commit...
echo ----------------------------------------

git diff --cached --quiet

if errorlevel 1 (
    git commit -m "Update VEDAI project"

    if errorlevel 1 (
        echo ERROR: Commit failed.
        pause
        exit /b 1
    )
) else (
    echo No new changes to commit.
)

echo.
echo ----------------------------------------
echo Setting branch to main...
echo ----------------------------------------

git branch -M main

echo.
echo ----------------------------------------
echo Checking remote...
echo ----------------------------------------

git remote -v

echo.

REM Check whether origin exists
git remote get-url origin >nul 2>&1

if errorlevel 1 (
    echo No GitHub remote named "origin" is configured.
    echo.
    echo Add your GitHub repository with:
    echo.
    echo git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
    echo.
    echo Then run this file again.
    echo.
    pause
    exit /b 1
)

echo ----------------------------------------
echo Pushing VEDAI to GitHub...
echo ----------------------------------------
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo PUSH FAILED
    echo ========================================
    echo.
    echo Check the error above.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo       VEDAI PUSH SUCCESSFUL!
echo ========================================
echo.

pause