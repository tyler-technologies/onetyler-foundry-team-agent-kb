@echo off
REM Double-click this on Windows. Nothing to type, no assistant needed.
REM
REM %~dp0 is this file's own folder, with a trailing slash - Explorer launches from
REM elsewhere, so cd first. `python`, not `python3`: the Windows launcher installs it as
REM `python`, and `python3` is a Microsoft Store stub that opens the Store instead.
cd /d "%~dp0"
python scripts\start.py
REM Keep the window open on failure so the error is readable rather than flashing past.
if errorlevel 1 pause
