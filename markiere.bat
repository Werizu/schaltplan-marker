@echo off
REM Schaltplan-Marker fuer Windows.
REM Nutzung: PDF-Datei auf diese .bat ziehen, oder:  markiere.bat plan.pdf
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Bitte eine PDF-Datei auf markiere.bat ziehen oder als Argument angeben.
  pause
  exit /b 1
)

REM Virtuelle Umgebung beim ersten Start anlegen
if not exist ".venv\Scripts\python.exe" (
  echo [Setup] Erstelle virtuelle Umgebung und installiere Abhaengigkeiten...
  py -3 -m venv .venv || python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
)

".venv\Scripts\python.exe" schaltplan_marker.py "%~1" --list
echo.
echo Fertig. Ergebnis liegt neben der Eingabe-PDF (..._markiert.pdf).
pause
