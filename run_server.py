"""
AutoParts CRM — Standalone launcher for .exe version.
Starts Django server and opens browser automatically.
"""
import os
import sys
import time
import threading
import webbrowser
import socket


def find_free_port(start=8000, end=9000):
    """Find an available port."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return 8000


def open_browser(port):
    """Open browser after a short delay."""
    time.sleep(2)
    webbrowser.open(f'http://127.0.0.1:{port}/')


def main():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoparts.settings')

    # If running as frozen exe, adjust paths
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    os.chdir(base_dir)
    sys.path.insert(0, base_dir)

    # Initialize Django
    import django
    django.setup()

    # Run migrations automatically
    from django.core.management import call_command
    print("🔧 Applying database migrations...")
    call_command('migrate', '--run-syncdb', verbosity=0)
    print("✅ Database ready")

    # Collect static files
    print("📦 Collecting static files...")
    call_command('collectstatic', '--noinput', verbosity=0)
    print("✅ Static files ready")

    # Find free port and start server
    port = find_free_port()
    print(f"\n🚀 AutoParts CRM starting on http://127.0.0.1:{port}/")
    print("   Press Ctrl+C to stop\n")

    # Open browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Start Django dev server
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'])


if __name__ == '__main__':
    main()
