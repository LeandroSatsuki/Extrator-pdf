@echo off
setlocal
cd /d "%~dp0\.."

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

echo Instalando dependencias...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Limpando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Gerando executavel Windows (onedir)...
"%PYTHON_EXE%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
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

echo Copiando arquivos externos para a distribuicao...
copy /Y "app.py" "dist\ExtratorPDF\app.py" >nul
xcopy /E /I /Y "src" "dist\ExtratorPDF\src" >nul
xcopy /E /I /Y "assets" "dist\ExtratorPDF\assets" >nul
xcopy /E /I /Y ".streamlit" "dist\ExtratorPDF\.streamlit" >nul
if not exist "dist\ExtratorPDF\data" mkdir "dist\ExtratorPDF\data"
if exist "data\.gitkeep" copy /Y "data\.gitkeep" "dist\ExtratorPDF\data\.gitkeep" >nul

echo Build concluido:
echo dist\ExtratorPDF\ExtratorPDF.exe
endlocal
