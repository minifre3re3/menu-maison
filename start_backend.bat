@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"

"%PYTHON%" -c "import flask, flask_cors, requests" >nul 2>&1
if errorlevel 1 (
    echo Dependances manquantes. Active l'environnement virtuel et lance :
    echo python -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "db\menu_maison.sqlite" "%PYTHON%" "db\creation_db\create_db.py"
start "API recherche - Menu Maison" /D "%~dp0" "%PYTHON%" "%~dp0db\backend_filtre.py"
start "API menus et stock - Menu Maison" /D "%~dp0" "%PYTHON%" "%~dp0db\backend_get_pages.py"
echo Les API sont demarrees. Ouvre frontend\index.html dans ton navigateur.
endlocal
