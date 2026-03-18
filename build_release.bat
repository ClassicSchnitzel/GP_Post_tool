@echo off
setlocal
cd /d "%~dp0"

echo Installing build dependencies...
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building standalone executable...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "GamingPenguinsPostingTool" ^
  --add-data "assets;assets" ^
  app.py
if errorlevel 1 exit /b 1

echo Creating release zip...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\GamingPenguinsPostingTool.exe' -DestinationPath 'dist\GamingPenguinsPostingTool-windows-x64.zip' -Force"
if errorlevel 1 exit /b 1

echo Done.
echo EXE: dist\GamingPenguinsPostingTool.exe
echo ZIP: dist\GamingPenguinsPostingTool-windows-x64.zip
