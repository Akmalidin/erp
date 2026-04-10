#!/usr/bin/env python
"""
AutoParts ERP — Desktop Launcher
Запускает Django-сервер и открывает браузер как десктопное приложение.
"""
import os
import sys
import socket
import threading
import time
import subprocess
import webbrowser
from pathlib import Path

HOST = '127.0.0.1'
PORT = 8765
URL  = f'http://{HOST}:{PORT}/'

# ── Пути ────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_BASE_DIR = Path(sys._MEIPASS)
    APP_DATA_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AutoPartsERP'
else:
    APP_BASE_DIR = Path(__file__).resolve().parent
    APP_DATA_DIR = APP_BASE_DIR

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ['APP_BASE_DIR'] = str(APP_BASE_DIR)
os.environ['APP_DATA_DIR'] = str(APP_DATA_DIR)

# ── Проверка доступности PostgreSQL сервера ──────────────────────────────────
PG_HOST = '46.149.68.65'
PG_PORT = 5432

def check_postgres(host=PG_HOST, port=PG_PORT, timeout=4):
    """Проверяем доступность именно PostgreSQL сервера, а не просто интернет."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        return True
    except OSError:
        return False


# ── Настройка БД ─────────────────────────────────────────────────────────────
online = check_postgres()
if online:
    os.environ['DB_NAME']     = 'erp_db'
    os.environ['DB_USER']     = 'erp_user'
    os.environ['DB_PASSWORD'] = 'ErpPass2024'
    os.environ['DB_HOST']     = '46.149.68.65'
    os.environ['DB_PORT']     = '5432'
    os.environ['DB_MODE']     = 'postgres'
    print('[AutoParts] Режим: PostgreSQL (онлайн)')
else:
    os.environ['DB_MODE'] = 'sqlite'
    # Явно блокируем PostgreSQL — settings.py читает .env и может подтянуть DB_NAME
    os.environ['DB_NAME'] = ''
    print('[AutoParts] Режим: SQLite (офлайн)')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoparts.settings')

# ── Django setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(APP_BASE_DIR))
import django
django.setup()

from django.core.management import call_command
try:
    call_command('migrate', '--run-syncdb', verbosity=0)
    print('[AutoParts] Миграции применены')
except Exception as e:
    print(f'[AutoParts] Ошибка миграций: {e}')

# ── Синхронизация данных ──────────────────────────────────────────────────────
if online:
    try:
        # Миграции на SQLite cache тоже нужны
        call_command('migrate', '--database', 'sqlite_cache', '--run-syncdb', verbosity=0)
        import sync_manager
        print('[AutoParts] Синхронизация данных...')
        pushed = sync_manager.push_offline_data()
        if pushed and (pushed[0] or pushed[1]):
            print(f'[AutoParts] Загружено на сервер: {pushed[0]} клиентов, {pushed[1]} заказов')
        sync_manager.pull_server_data()
        print('[AutoParts] Данные синхронизированы с сервером')
    except Exception as e:
        print(f'[AutoParts] Ошибка синхронизации: {e}')

# ── Фоновый мониторинг подключения ───────────────────────────────────────────
_connectivity_file = APP_DATA_DIR / '.connectivity'

def _write_connectivity(status: str):
    """Пишем статус в файл, который Django-view читает для фронтенда."""
    try:
        _connectivity_file.write_text(status)
    except Exception:
        pass

_write_connectivity('postgres' if online else 'sqlite')

def _monitor_connectivity():
    """Проверяет доступность PostgreSQL каждые 20 сек."""
    prev = online
    while True:
        time.sleep(20)
        now = check_postgres()
        if now != prev:
            _write_connectivity('postgres' if now else 'sqlite')
            prev = now

threading.Thread(target=_monitor_connectivity, daemon=True).start()

# ── Открыть браузер в app-режиме ─────────────────────────────────────────────
def _open_browser():
    time.sleep(2)
    app_exe = None
    candidates = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    ]
    for exe in candidates:
        if Path(exe).exists():
            app_exe = exe
            break

    profile_dir = str(APP_DATA_DIR / 'browser_profile')
    if app_exe:
        subprocess.Popen([
            app_exe,
            f'--app={URL}',
            '--disable-extensions',
            f'--user-data-dir={profile_dir}',
            '--window-size=1280,800',
        ])
    else:
        webbrowser.open(URL)

threading.Thread(target=_open_browser, daemon=True).start()

# ── Запуск Django сервера ─────────────────────────────────────────────────────
print(f'[AutoParts] Сервер запускается на {URL}')
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'runserver', f'{HOST}:{PORT}', '--noreload'])
