@echo off
chcp 65001 >nul
echo ============================================================
echo   AutoParts ERP — Сборка десктопного приложения
echo ============================================================

:: Проверяем python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    pause & exit /b 1
)

:: Устанавливаем зависимости
echo.
echo [1/5] Установка зависимостей...
pip install -r requirements.txt -q
pip install pyinstaller -q

:: Сбор статики
echo.
echo [2/5] Сбор статических файлов...
python manage.py collectstatic --noinput -v 0

:: Создаём папку dist если нет
if not exist dist mkdir dist

:: Собираем exe
echo.
echo [3/5] Сборка EXE через PyInstaller...
pyinstaller --noconfirm --clean ^
  --name "AutoPartsERP" ^
  --onefile ^
  --windowed ^
  --icon "static/img/favicon.ico" ^
  --add-data "templates;templates" ^
  --add-data "staticfiles;staticfiles" ^
  --add-data "autoparts;autoparts" ^
  --add-data "users;users" ^
  --add-data "catalog;catalog" ^
  --add-data "orders;orders" ^
  --add-data "crm;crm" ^
  --add-data "warehouse;warehouse" ^
  --add-data "purchases;purchases" ^
  --add-data "reports;reports" ^
  --add-data "portal;portal" ^
  --add-data "desktop;desktop" ^
  --hidden-import "django.contrib.admin" ^
  --hidden-import "django.contrib.auth" ^
  --hidden-import "django.contrib.contenttypes" ^
  --hidden-import "django.contrib.sessions" ^
  --hidden-import "django.contrib.messages" ^
  --hidden-import "django.contrib.staticfiles" ^
  --hidden-import "django.contrib.humanize" ^
  --hidden-import "whitenoise" ^
  --hidden-import "psycopg2" ^
  --hidden-import "PIL" ^
  --hidden-import "pandas" ^
  --hidden-import "openpyxl" ^
  --collect-all "django" ^
  run_server.py

echo.
echo [4/5] Создание папки для данных...
if not exist "dist\AutoPartsERP_data" mkdir "dist\AutoPartsERP_data"

echo.
echo [5/5] Создание ярлыка запуска...
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" "AutoPartsERP.exe"
) > "dist\Запустить AutoParts.bat"

echo.
echo ============================================================
echo   ГОТОВО! Файл: dist\AutoPartsERP.exe
echo ============================================================
pause
