# Build with: .venv\Scripts\python.exe -m PyInstaller BatteryLineSimulator.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['desktop_launcher.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('pyvista') + collect_data_files('pyvistaqt'),
    hiddenimports=collect_submodules('pyvista') + collect_submodules('pyvistaqt'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'IPython', 'pytest'],
    noarchive=False,
)
# Qt uses Windows' native ICU. An unrelated Poppler directory on PATH can
# cause bindepend to collect its incompatible icuuc.dll instead of the OS DLL.
a.binaries = [item for item in a.binaries
              if not (item[0].lower() == 'icuuc.dll'
                      or '/native/poppler/' in item[1].replace('\\', '/').lower())]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='BatteryLineSimulator', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='BatteryLineSimulator')
