# PyInstaller spec — builds dist/QASSIMZ Organizer/ (one-folder = fast startup)
from PyInstaller.utils.hooks import collect_all
datas = [("app/ui", "app/ui"), ("assets", "assets"), ("README.md", "."), ("docs", "docs")]
binaries, hiddenimports = [], []
for pkg in ("webview", "pystray"):
    d, b, h = collect_all(pkg); datas += d; binaries += b; hiddenimports += h

a = Analysis(["app/main.py"], pathex=["app"], datas=datas, binaries=binaries,
             hiddenimports=hiddenimports + ["core"], excludes=["tkinter", "numpy"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="QASSIMZ Organizer",
          icon="assets/logo.ico", console=False, version="installer/version.txt")
coll = COLLECT(exe, a.binaries, a.datas, name="QASSIMZ Organizer")
