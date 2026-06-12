"""
PyInstaller build script — creates standalone executables
Run: pyinstaller build_spec.py
"""
import PyInstaller.config
from PyInstaller.utils.hooks import collect_all, get_module_file_attribute
import os

# Collect all data from dependencies
datas = []
datas += collect_all('streamlit')
datas += collect_all('plotly')

# Add local config files
datas.append(('config.py', '.'))
datas.append(('.env', '.'))

# Bot executable
bot_a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'colorlog',
        'ccxt',
        'pandas',
        'numpy',
        'sklearn',
        'streamlit',
        'plotly',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

bot_pyz = PYZ(bot_a.pure, bot_a.zipped_data, cipher=None)

bot_exe = EXE(
    bot_pyz,
    bot_a.scripts,
    bot_a.binaries,
    bot_a.zipfiles,
    bot_a.datas,
    [],
    name='trading_bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

# Dashboard executable
dash_a = Analysis(
    ['dashboard.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'plotly',
        'pandas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

dash_pyz = PYZ(dash_a.pure, dash_a.zipped_data, cipher=None)

dash_exe = EXE(
    dash_pyz,
    dash_a.scripts,
    dash_a.binaries,
    dash_a.zipfiles,
    dash_a.datas,
    [],
    name='dashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)

coll = COLLECT(
    bot_exe,
    bot_a.binaries,
    bot_a.zipfiles,
    bot_a.datas,
    dash_exe,
    dash_a.binaries,
    dash_a.zipfiles,
    dash_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TradingBot',
)
