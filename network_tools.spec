# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Base and data collection
added_files = [
    ('web', 'web'),
    ('server', 'server'),
    ('config.json', '.'),
    ('network-analysis.ico', '.'),
    ('playbooks', 'playbooks')
]

a = Analysis(
    ['build_exe.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'sqlalchemy.ext.baked', # Just in case SQLAlchemy components are used
        'pysnmp.smi.mibs',      # Important for SNMP
        'pysnmp.smi.mibs.instances',
        'pysnmp.debug',
        'pyasyncore', # Needed for newer Python with pysnmp/nmap
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
    [],
    exclude_binaries=True,
    name='NetworkToolsV3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False for standard GUI (no console), but for debugging it's safer True
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['network-analysis.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NetworkTools',
)
