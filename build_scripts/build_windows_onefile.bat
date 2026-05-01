@echo off
setlocal
cd /d "%~dp0\.."

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

echo Instalando dependencias...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Limpando build anterior...
if exist "build" rmdir /s /q "build"

echo Gerando executavel Windows (onefile)...
"%PYTHON_EXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name ExtratorPDF ^
  --collect-all streamlit ^
  --collect-all pdfplumber ^
  --collect-all pdfminer ^
  --collect-all reportlab ^
  --add-data "app.py;." ^
  --add-data "src;src" ^
  --add-data "assets;assets" ^
  --add-data ".streamlit;.streamlit" ^
  --hidden-import streamlit ^
  --hidden-import streamlit.web.cli ^
  launcher.py
if errorlevel 1 exit /b 1

echo Build concluido:
echo dist\ExtratorPDF.exe
endlocal
