@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo             ORINDA INSTALLER FOR WINDOWS
echo ===================================================
echo This script will set up Orinda, a LLM and RAG application
echo.

REM Check for Python installation
echo Checking for Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.8 or higher.
    echo You can download Python from https://www.python.org/downloads/
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set pyversion=%%i
echo Found Python %pyversion%

REM Check for pip
echo Checking for pip...
python -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo pip not found. Installing pip...
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    del get-pip.py
)

REM Check for virtualenv
echo Checking for virtualenv...
python -m pip show virtualenv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo virtualenv not found. Installing virtualenv...
    python -m pip install virtualenv
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m virtualenv venv
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install pillow pyperclip langchain langchain_community chromadb ollama unstructured numpy

REM Check if Ollama is installed
echo Checking for Ollama...
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Ollama not found in PATH.
    echo Please install Ollama from https://ollama.ai/download
    echo After installation, run:
    echo   ollama pull llama3:latest
    echo   ollama pull llama3.2:latest
    echo.
    echo Do you want to continue anyway? (Y/N)
    set /p continue=
    if /i not "!continue!"=="Y" (
        echo Installation aborted.
        exit /b 1
    )
) else (
    echo Ollama found in PATH.
    
    echo Pulling required models...
    echo This might take a while depending on your internet connection.
    
    echo Pulling llama3.2:latest...
    ollama pull llama3.2:latest
    
    echo Pulling llama3:latest...
    ollama pull llama3:latest
    
    echo Pulling nomic-embed-text for embeddings...
    ollama pull nomic-embed-text
)

REM Create a launcher script
echo Creating launcher...
echo @echo off > run_orinda.bat
echo call venv\Scripts\activate.bat >> run_orinda.bat
echo python main.py >> run_orinda.bat
echo pause >> run_orinda.bat

echo.
echo ===================================================
echo Installation complete!
echo.
echo To run Orinda, double-click on run_orinda.bat
echo or run it from the command line.
echo ===================================================
echo.

echo Press any key to exit...
pause >nul

endlocal
