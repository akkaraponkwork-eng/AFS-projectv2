@echo off
echo Starting Auto-Fill Web App...

if not exist "venv\Scripts\activate.bat" (
    echo [!] Virtual environment not found. Running setup.bat first...
    call setup.bat
)

call venv\Scripts\activate
python app.py
pause
