# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for AutoParts CRM.

Usage:
    pyinstaller build.spec
"""

import os

block_cipher = None
base_dir = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['run_server.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('autoparts', 'autoparts'),
        ('users', 'users'),
        ('catalog', 'catalog'),
        ('warehouse', 'warehouse'),
        ('orders', 'orders'),
        ('crm', 'crm'),
        ('reports', 'reports'),
        ('purchases', 'purchases'),
    ],
    hiddenimports=[
        'django',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.humanize',
        'users',
        'catalog',
        'warehouse',
        'orders',
        'crm',
        'reports',
        'purchases',
        'pandas',
        'openpyxl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoPartsCRM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
