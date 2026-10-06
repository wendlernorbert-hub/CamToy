@echo off
REM Baut dist\CamToy.exe (eine einzelne Datei, enthaelt Python, Modelle und Sounds).
REM Einstellungen (enthaltene Dateien, ausgeschlossene Pakete) stehen in CamToy.spec.
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean CamToy.spec
echo.
echo Fertig: dist\CamToy.exe
