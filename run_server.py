"""
AutoParts CRM — Desktop launcher.
Starts a threaded wsgiref server then opens a native pywebview window.
No browser, no Django dev server, no autoreload.
"""
import os
import sys
import time
import socket
import threading


def find_free_port(start=8765):
    for port in range(start, start + 200):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start


def wait_for_server(port, timeout=30):
    """Block until Django is accepting connections (max timeout seconds)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def run_django(port):
    """Initialize Django and serve via threaded wsgiref. Runs forever."""
    import django
    django.setup()

    # Apply migrations on every start (fast no-op if already applied)
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)

    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
    from socketserver import ThreadingMixIn

    class _QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            pass  # suppress per-request logs

    class _ThreadedWSGI(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    app = get_wsgi_application()
    srv = _ThreadedWSGI(('127.0.0.1', port), _QuietHandler)
    srv.set_app(app)
    srv.serve_forever()


def _setup_paths():
    """
    Determine base_dir (app code / templates / static) and data_dir
    (writable: database, media).  Returns (base_dir, data_dir) as strings.
    """
    frozen = getattr(sys, 'frozen', False)

    if frozen:
        # PyInstaller COLLECT mode places bundled files in _MEIPASS
        # (_internal/ next to the .exe).
        base_dir = sys._MEIPASS
        appdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        data_dir = os.path.join(appdata, 'AutoPartsCRM')
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = base_dir

    return base_dir, data_dir


def main():
    base_dir, data_dir = _setup_paths()

    os.makedirs(data_dir, exist_ok=True)

    # Ensure app packages are importable
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    os.chdir(base_dir)

    # Tell settings.py where to find app files and where to write data
    os.environ['DJANGO_SETTINGS_MODULE'] = 'autoparts.settings'
    os.environ['APP_BASE_DIR'] = base_dir
    os.environ['APP_DATA_DIR'] = data_dir

    port = find_free_port()

    # Start Django in a daemon thread so the process exits when the window closes
    t = threading.Thread(target=run_django, args=(port,), daemon=True)
    t.start()

    # Wait until the server is ready before opening the window
    if not wait_for_server(port, timeout=30):
        print('ERROR: Django server did not start within 30 seconds', file=sys.stderr)
        sys.exit(1)

    # Open native desktop window (no browser)
    import webview
    webview.create_window(
        'AutoParts CRM',
        f'http://127.0.0.1:{port}/',
        width=1440,
        height=900,
        min_size=(1024, 700),
    )
    webview.start(debug=False)


if __name__ == '__main__':
    main()
