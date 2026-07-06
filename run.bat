@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem The Anthropic/Runway/ElevenLabs SDKs crash on Python 3.14 with:
rem   'typing.Union' object has no attribute '__discriminator__'
rem (Python 3.14 made typing.Union immutable; the SDKs' generated code hasn't
rem caught up yet). So we prefer 3.13/3.12/3.11 over whatever "python" points to.
set PYCMD=

for %%V in (3.13 3.12 3.11) do (
    if "!PYCMD!"=="" (
        py -%%V -c "" >nul 2>nul
        if !errorlevel! == 0 set PYCMD=py -%%V
    )
)

if "!PYCMD!"=="" (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set FOUND_VER=%%v
    echo !FOUND_VER! | findstr /b "3.14" >nul
    if !errorlevel! == 0 (
        echo.
        echo WARNING: Only Python 3.14 was found ^(!FOUND_VER!^).
        echo This project's SDKs currently crash on 3.14 with a typing.Union error.
        echo Install Python 3.12 or 3.13 from python.org, or run:
        echo     winget install Python.Python.3.12
        echo Continuing with 3.14 anyway - film generation will likely fail.
        echo.
    )
    set PYCMD=python
)

echo Using interpreter: !PYCMD!
!PYCMD! -m venv .venv 2>nul
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
