@echo off
:: =================================================================
::  Strader Build Script - Portable Version
:: =================================================================
echo.
echo  Step 1: Finding the path to vaderSentiment package...
echo.

:: Find vaderSentiment path and saves it to a variable called VADER_PATH
FOR /F "delims=" %%i IN ('python -c "import vaderSentiment, os; print(os.path.dirname(vaderSentiment.__file__))"') DO (
    SET VADER_PATH=%%i
)

:: Check if the path was found
IF NOT DEFINED VADER_PATH (
    echo ERROR: Could not find the path for vaderSentiment.
    echo Please make sure 'vaderSentiment' is installed in your active Python environment.
    pause
    exit /b
)

echo  Found vaderSentiment at: %VADER_PATH%
echo.
echo  Step 2: Starting the PyInstaller build...
echo.

:: Clean up old build files before starting a new one
IF EXIST build rmdir /s /q build
IF EXIST dist rmdir /s /q dist
IF EXIST strader.spec del strader.spec

:: Run the PyInstaller command
pyinstaller ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --collect-all en_core_web_sm ^
    --collect-data nltk ^
    --collect-data textblob ^
    --add-data "assets;assets" ^
    --add-data "%VADER_PATH%;vaderSentiment" ^
    --icon=assets/bbstrader.ico ^
    -n strader ^
    strader/__main__.py

echo.
echo ===================================================
echo  Build Complete!
echo  Check the 'dist' folder for strader.exe
echo ===================================================
echo.
pause
