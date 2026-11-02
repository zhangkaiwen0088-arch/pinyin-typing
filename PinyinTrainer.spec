# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file build for the pinyin typing trainer.

Run through build_exe.bat, which uses the Python environment at C:\\py.
"""

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files

env_dir = Path(sys.executable).resolve().parent
bin_dir = env_dir / "Library" / "bin"
lib_dir = env_dir / "Library" / "lib"

datas = [("sentences.txt", ".")]
datas += collect_data_files("pypinyin")
datas += [
    (str(lib_dir / "tcl8.6"), "_tcl_data"),
    (str(lib_dir / "tk8.6"), "_tk_data"),
    (str(lib_dir / "tcl8"), "tcl8"),
]

binaries = [
    (str(bin_dir / name), ".")
    for name in (
        "tcl86t.dll",
        "tk86t.dll",
        "ffi-8.dll",
        "libmpdec-4.dll",
        "libcrypto-3-x64.dll",
        "libssl-3-x64.dll",
        "zstd.dll",
        "liblzma.dll",
        "libbz2.dll",
    )
    if (bin_dir / name).exists()
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PinyinTrainer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
