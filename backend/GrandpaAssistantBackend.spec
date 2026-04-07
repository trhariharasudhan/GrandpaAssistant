# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path.cwd()
backend_root = project_root / "backend"

hiddenimports = []
for package_name in [
    "app",
    "agents",
    "shared",
    "brain",
    "cognition",
    "security",
    "features",
    "voice",
    "vision",
    "modules",
    "utils",
]:
    hiddenimports.extend(collect_submodules(package_name))

hiddenimports.extend(
    [
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ]
)

datas = [
    (str(project_root / "backend"), "backend"),
    (str(project_root / "docs"), "docs"),
    (str(project_root / ".env.example"), "."),
    (str(project_root / "README.md"), "."),
]

a = Analysis(
    [str(backend_root / "desktop_backend_boot.py")],
    pathex=[
        str(project_root),
        str(backend_root),
        str(backend_root / "app"),
        str(backend_root / "app" / "shared"),
        str(backend_root / "app" / "features"),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GrandpaAssistantBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GrandpaAssistantBackend",
)
