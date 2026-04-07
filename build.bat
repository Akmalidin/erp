@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  AutoParts CRM — Build Script
echo ============================================================
echo.

:: ── Check that we are in the project directory ──────────────────────────────
if not exist "manage.py" (
    echo ERROR: Run this script from the project root ^(where manage.py is^).
    pause & exit /b 1
)

:: ── Step 1: Collect static files ────────────────────────────────────────────
echo [1/3] Collecting static files...
python manage.py collectstatic --noinput --clear
if errorlevel 1 (
    echo ERROR: collectstatic failed.
    pause & exit /b 1
)
echo       Done. staticfiles\ is ready.
echo.

:: ── Step 2: Run PyInstaller ─────────────────────────────────────────────────
echo [2/3] Building exe with PyInstaller...
pyinstaller build.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause & exit /b 1
)
echo       Done. dist\AutoPartsCRM\ is ready.
echo.

:: ── Step 3: Build Inno Setup installer (optional) ───────────────────────────
echo [3/3] Building installer with Inno Setup...

:: Try common ISCC locations
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if %ISCC%=="" (
    echo       Inno Setup not found — skipping installer build.
    echo       Install from https://jrsoftware.org/isinfo.php then run:
    echo         ISCC installer.iss
) else (
    %ISCC% installer.iss
    if errorlevel 1 (
        echo ERROR: Inno Setup build failed.
        pause & exit /b 1
    )
    echo       Installer: dist\AutoPartsCRM_Setup_v1.0.exe
)

echo.
echo ============================================================
echo  Build complete!
echo  App folder : dist\AutoPartsCRM\
echo  Installer  : dist\AutoPartsCRM_Setup_v1.0.exe
echo ============================================================
pause
