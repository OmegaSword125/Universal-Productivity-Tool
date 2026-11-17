@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
  echo UPT needs its local Python environment first.
  echo Follow the Windows setup commands in README.md.
  pause
  exit /b 1
)
start "UPT" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run_upt.py" %*
