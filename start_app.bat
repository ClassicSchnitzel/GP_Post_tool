@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python-Umgebung nicht gefunden: .venv\Scripts\python.exe
  echo Bitte zuerst im Projektordner ausfuehren:
  echo   py -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo Die App wurde mit einem Fehler beendet.
  echo Siehe ggf. startup_error.log im Projektordner.
  pause
)
