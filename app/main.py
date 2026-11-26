"""QASSIMZ Organizer — desktop app (pywebview + Architectural File Blueprint Studio UI).

Runs on its own: auto-organizes watched folders in the background, lives in the
system tray, starts with Windows, and updates itself from QASSIMZ Hub / GitHub Releases.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from dataclasses import asdict
from pathlib import Path

# Guard windowed PyInstaller builds where stdout / stderr are None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import webview  # pywebview

import core

APP_NAME = "QASSIMZ Organizer"
APP_ID = "qassimz-organizer"
VERSION = "1.1.0"
REPO = "ahmedqassimtv-commits/qassimz-organizer"
CATALOG_URL = "https://raw.githubusercontent.com/ahmedqassimtv-commits/qassimz-hub/main/catalog.json"
GITHUB_URL = f"https://github.com/{REPO}"
SUPPORT_URL = f"https://github.com/{REPO}/issues"
SITE_URL = "https://qassimz.com"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
IPC_PORT_FILE = DATA_DIR / "instance.port"

ARGS = sys.argv[1:]
BACKGROUND = "--background" in ARGS
# opened from the Explorer right-click menu: "رتّب بـ QASSIMZ Organizer"
START_FOLDER = next((str(Path(a).resolve()) for a in ARGS if not a.startswith("-") and os.path.isdir(a)), "")

DEFAULTS = {
    "lang": "ar", "rename": True, "subkinds": True, "duplicates": True, "by_date": False,
    "recursive": False, "include_color": True,
    "auto": False, "auto_folders": [str(Path.home() / "Downloads")], "auto_interval": 10,
    "auto_update": True, "welcomed": False, "last_auto": None,
}

_MUTEX_HANDLE = None
_LOCK_FILE = None


def resource(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
    return str(Path(base) / rel)


def settings_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "settings.json"


def load_settings() -> dict:
    s = dict(DEFAULTS)
    try:
        s.update(json.loads(settings_path().read_text(encoding="utf-8")))
    except Exception:
        pass
    return s


def save_settings(s: dict):
    try:
        settings_path().write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _ver(t: str) -> tuple:
    try:
        return tuple(int(x) for x in t.strip().lstrip("vV").split(".")[:3])
    except Exception:
        return (0,)


# ------------------------------------------------------- Single-instance & IPC
def _acquire_single_instance() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            handle = kernel32.CreateMutexW(None, False, "Local\\QASSIMZ_Organizer_SingleInstance_v1")
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                if handle:
                    kernel32.CloseHandle(handle)
                return False
            global _MUTEX_HANDLE
            _MUTEX_HANDLE = handle
            return True
        except Exception:
            return True
    else:
        try:
            import fcntl
            lf = open(DATA_DIR / "instance.lock", "w", encoding="utf-8")
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                lf.close()
                return False
            global _LOCK_FILE
            _LOCK_FILE = lf
            return True
        except Exception:
            return True


def _forward_to_running_instance(payload: str) -> bool:
    for _ in range(15):
        try:
            port = int(IPC_PORT_FILE.read_text(encoding="utf-8").strip())
            with socket.create_connection(("127.0.0.1", port), timeout=1.0) as conn:
                conn.sendall(payload.encode("utf-8"))
            return True
        except Exception:
            time.sleep(0.1)
    return False


def _start_ipc_server(api: "Api"):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        try:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except Exception:
            pass
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    port = srv.getsockname()[1]
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        IPC_PORT_FILE.write_text(str(port), encoding="utf-8")
    except Exception:
        pass

    def serve():
        while not api._quit:
            try:
                conn, _ = srv.accept()
            except Exception:
                break
            try:
                with conn:
                    conn.settimeout(2.0)
                    msg = conn.recv(4096).decode("utf-8", errors="replace").strip()
                if not msg or msg == "NOOP":
                    continue
                if msg != "SHOW" and os.path.isdir(msg):
                    api.activate_folder(msg)
                else:
                    api.show()
            except Exception:
                pass

    threading.Thread(target=serve, daemon=True).start()
    return srv


# ------------------------------------------------------- Window / WebView2 UX
def _apply_dark_titlebar():
    if os.name != "nt":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, APP_NAME)
        if hwnd:
            dwm = ctypes.windll.dwmapi
            dark = ctypes.c_int(1)
            caption = ctypes.c_int(0x000C0D09)  # COLORREF 0x00BBGGRR -> #090D0C
            text = ctypes.c_int(0x00F3F6F4)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
            dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), 4)
            dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), 4)
    except Exception:
        pass


def _focus_window(win, bring_to_front: bool = False):
    if not win:
        return
    if bring_to_front:
        try:
            win.on_top = True
            win.on_top = False
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, APP_NAME)
            if hwnd:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                if bring_to_front:
                    user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
        except Exception:
            pass
        try:
            from System import Action  # type: ignore
            from webview.platforms import winforms  # type: ignore
            form = winforms.BrowserView.instances.get(win.uid)
            if form is not None:
                form.Invoke(Action(lambda: (form.Activate() if bring_to_front else None, form.webview.Focus())))
        except Exception:
            pass
    try:
        win.evaluate_js("window.focus && window.focus();")
    except Exception:
        pass


# ------------------------------------------------------------ Windows startup
def startup_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_startup(on: bool):
    if os.name != "nt":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            if getattr(sys, "frozen", False):
                cmd = f'"{sys.executable}" --background'
            else:
                script = Path(__file__).resolve()
                pyw = Path(sys.executable).with_name("pythonw.exe")
                exe = pyw if pyw.exists() else Path(sys.executable)
                cmd = f'"{exe}" "{script}" --background'
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except OSError:
                pass


# ===================================================================== API
class Api:
    def __init__(self):
        self.window = None
        self.tray = None
        self.plan = None
        self._busy = False
        self._quit = False
        self._pending_folder = START_FOLDER
        self.settings = load_settings()
        self.update = None          # {"version", "url", "notes"}
        self._wake = threading.Event()

    # ----------------------------------------------------------- helpers
    def _emit(self, event: str, data):
        if self.window:
            try:
                self.window.evaluate_js(
                    f"window.onBackend && window.onBackend({json.dumps(event)}, {json.dumps(data, ensure_ascii=False)})")
            except Exception:
                pass

    def _notify(self, msg: str):
        if self.tray:
            try:
                self.tray.notify(msg, APP_NAME)
            except Exception:
                pass

    def info(self):
        sf = self._pending_folder or START_FOLDER
        self._pending_folder = ""
        return {"name": APP_NAME, "version": VERSION, "github": GITHUB_URL, "support": SUPPORT_URL,
                "site": SITE_URL, "downloads": str(Path.home() / "Downloads"),
                "desktop": str(Path.home() / "Desktop"), "start_folder": sf,
                "startup": startup_enabled(), "update": self.update}

    def load_settings(self):
        return self.settings

    def save_settings(self, s):
        was_auto = self.settings.get("auto")
        self.settings.update(s or {})
        save_settings(self.settings)
        if self.settings.get("auto") and not was_auto:
            self._wake.set()
        return True

    def set_startup(self, on: bool):
        try:
            set_startup(bool(on))
            return startup_enabled()
        except Exception as e:
            return {"error": str(e)}

    def pick_folder(self):
        r = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return r[0] if r else ""

    def open_url(self, url):
        webbrowser.open(url)

    def open_folder(self, path):
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            webbrowser.open(Path(path).as_uri())

    def open_readme(self):
        p = resource("README.md")
        if os.path.exists(p) and os.name == "nt":
            os.startfile(p)  # type: ignore[attr-defined]
        else:
            webbrowser.open(GITHUB_URL + "#readme")

    # ------------------------------------------------------- manual work
    def _opts(self, folder: str, overrides: dict | None = None) -> core.Options:
        d = {**self.settings, **(overrides or {}), "folder": folder}
        return core.Options(**{k: v for k, v in d.items() if k in core.Options.__dataclass_fields__})

    def scan(self, opts: dict):
        if self._busy:
            return False
        self._busy = True

        def run():
            try:
                o = self._opts(opts.get("folder", ""), opts)
                plan = core.build_plan(o, progress=lambda i, n, name: self._emit(
                    "progress", {"i": i, "n": n, "name": name, "phase": "scan"}))
                self.plan = asdict(plan)
                self._emit("plan", self.plan)
            except Exception as ex:
                self._emit("error", str(ex))
            finally:
                self._busy = False

        threading.Thread(target=run, daemon=True).start()
        return True

    def apply(self, excluded: list):
        if self._busy or not self.plan:
            return False
        self._busy = True
        ex = set(excluded or [])
        plan = dict(self.plan)
        plan["items"] = [it for it in self.plan["items"] if it["src"] not in ex]

        def run():
            try:
                r = core.apply_plan(plan, progress=lambda i, n, name: self._emit(
                    "progress", {"i": i, "n": n, "name": name, "phase": "apply"}))
                self.plan = None
                self._emit("applied", {"moved": r["moved"], "errors": r["errors"], "folder": plan["folder"]})
            except Exception as e:
                self._emit("error", str(e))
            finally:
                self._busy = False

        threading.Thread(target=run, daemon=True).start()
        return True

    def undo(self, folder: str):
        try:
            return core.undo_last(folder)
        except Exception as e:
            return {"restored": 0, "errors": 1, "message": str(e)}

    def history(self, folder: str):
        return core.history(folder)

    # -------------------------------------------------------- auto mode
    def organize_now(self):
        self._wake.set()
        return True

    def _auto_once(self) -> int:
        total = 0
        for folder in self.settings.get("auto_folders") or []:
            if not os.path.isdir(folder):
                continue
            try:
                plan = core.build_plan(self._opts(folder))
                todo = [it for it in asdict(plan)["items"] if it["src"] != it["dst"] and it["status"] != "error"]
                if todo:
                    r = core.apply_plan({"folder": plan.folder, "items": todo})
                    total += r["moved"]
            except Exception:
                pass
        self.settings["last_auto"] = time.strftime("%Y-%m-%d %H:%M")
        save_settings(self.settings)
        return total

    def auto_loop(self):
        self._wake.wait(8)  # let Windows finish booting / downloads settle
        self._wake.clear()
        while not self._quit:
            if self.settings.get("auto") and not self._busy:
                self._busy = True
                try:
                    moved = self._auto_once()
                finally:
                    self._busy = False
                self._emit("auto", {"moved": moved, "at": self.settings["last_auto"]})
                if moved:
                    self._notify(f"اترتب {moved} ملف تلقائياً ✓")
            mins = max(1, int(self.settings.get("auto_interval") or 10))
            self._wake.wait(mins * 60)
            self._wake.clear()

    # ----------------------------------------------------------- update
    def _set_found_update(self, version: str, url: str, notes: str, silent: bool):
        self.update = {"version": version.lstrip("vV"), "url": url, "notes": (notes or "")[:600]}
        self._emit("update", self.update)
        if silent:
            self._notify(f"فيه تحديث جديد {self.update['version']} — افتح البرنامج وحدّث بضغطة")
        return self.update

    def check_update(self, silent: bool = False):
        ctx = _ssl_context()
        # 1. Primary: QASSIMZ Hub catalog.json (zero GitHub API rate-limit pressure)
        try:
            req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "QASSIMZ-Organizer"})
            with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
                cat = json.loads(r.read().decode("utf-8"))
            apps = cat.get("apps") if isinstance(cat, dict) else None
            entry = None
            if isinstance(apps, dict):
                entry = apps.get(APP_ID)
            elif isinstance(apps, list):
                entry = next((x for x in apps if isinstance(x, dict) and (
                    x.get("id") == APP_ID or x.get("slug") == APP_ID or str(x.get("repo", "")).endswith(APP_ID)
                )), None)
            if isinstance(entry, dict):
                ver = str(entry.get("version") or entry.get("latest_version") or entry.get("latest") or entry.get("tag_name") or "").strip()
                url = (entry.get("setup_url") or entry.get("installer_url") or entry.get("download_url") or entry.get("url") or "")
                if not url and isinstance(entry.get("assets"), dict):
                    url = entry["assets"].get("setup") or entry["assets"].get("installer") or entry["assets"].get("url") or ""
                notes = str(entry.get("notes") or entry.get("release_notes") or entry.get("changelog") or entry.get("body") or "")
                if _ver(ver) != (0,):
                    if _ver(ver) > _ver(VERSION):
                        if isinstance(url, str) and url.startswith("https://"):
                            return self._set_found_update(ver, url, notes, silent)
                    else:
                        return {"latest": True}
        except Exception:
            pass

        # 2. Fallback: GitHub Releases API
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                         headers={"User-Agent": "QASSIMZ-Organizer",
                                                  "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                rel = json.loads(r.read().decode("utf-8"))
            tag = rel.get("tag_name", "")
            asset = next((a for a in rel.get("assets", [])
                          if a["name"].lower().endswith(".exe") and "setup" in a["name"].lower()), None)
            if _ver(tag) > _ver(VERSION) and asset:
                return self._set_found_update(tag, asset["browser_download_url"], rel.get("body") or "", silent)
            return {"latest": True}
        except Exception as e:
            return {"error": str(e)}

    def install_update(self):
        if not self.update:
            return False

        def run():
            try:
                ctx = _ssl_context()
                dst = Path(tempfile.gettempdir()) / f"QASSIMZ-Organizer-Setup-{self.update['version']}.exe"
                req = urllib.request.Request(self.update["url"], headers={"User-Agent": "QASSIMZ-Organizer"})
                with urllib.request.urlopen(req, timeout=60, context=ctx) as r, open(dst, "wb") as f:
                    size = int(r.headers.get("Content-Length") or 0)
                    got = 0
                    while chunk := r.read(1 << 16):
                        f.write(chunk)
                        got += len(chunk)
                        if size:
                            self._emit("update_progress", round(got * 100 / size))
                # silent install; the installer relaunches the app when done
                subprocess.Popen([str(dst), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"])
                self.quit()
            except Exception as e:
                self._emit("error", f"التحديث فشل: {e}")

        threading.Thread(target=run, daemon=True).start()
        return True

    # ------------------------------------------------------------ window
    def activate_folder(self, folder: str):
        self._pending_folder = folder
        self.show()
        self._emit("open_folder", folder)

    def show(self):
        if self.window:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass
            _focus_window(self.window, bring_to_front=True)

    def quit(self):
        self._quit = True
        self._wake.set()
        try:
            IPC_PORT_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        os._exit(0)


# =================================================================== tray
def start_tray(api: Api):
    try:
        import pystray
        from PIL import Image
    except Exception:
        return
    img = Image.open(resource("assets/logo.png"))

    def toggle_auto(icon=None, item=None):
        api.save_settings({"auto": not api.settings.get("auto")})
        api._emit("settings", api.settings)

    menu = pystray.Menu(
        pystray.MenuItem("افتح QASSIMZ Organizer", lambda icon, item: api.show(), default=True),
        pystray.MenuItem("رتّب دلوقتي", lambda icon, item: api.organize_now()),
        pystray.MenuItem("الترتيب التلقائي", toggle_auto, checked=lambda item: bool(api.settings.get("auto"))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("خروج", lambda icon, item: api.quit()),
    )
    api.tray = pystray.Icon("qassimz-organizer", img, APP_NAME, menu)
    api.tray.run_detached()


def main():
    if not _acquire_single_instance():
        if BACKGROUND and not START_FOLDER:
            sys.exit(0)
        _forward_to_running_instance(START_FOLDER or "SHOW")
        sys.exit(0)

    api = Api()
    _start_ipc_server(api)

    webview_storage = DATA_DIR / "webview"
    webview_storage.mkdir(parents=True, exist_ok=True)

    win = webview.create_window(
        APP_NAME, url=resource("app/ui/index.html"), js_api=api,
        width=1220, height=800, min_size=(980, 640), background_color="#090D0C",
        text_select=False, hidden=BACKGROUND,
    )
    api.window = win

    def on_shown():
        _apply_dark_titlebar()
        if not BACKGROUND:
            _focus_window(win, bring_to_front=False)

    def on_loaded():
        if not BACKGROUND:
            _focus_window(win, bring_to_front=False)

    def on_closing():
        # keep working from the tray when auto-organize is on
        if api.settings.get("auto") and api.tray and not api._quit:
            win.hide()
            api._notify("البرنامج شغال في الخلفية وبيرتب لوحده — هتلاقيه جنب الساعة")
            return False
        api.quit()

    win.events.shown += on_shown
    win.events.loaded += on_loaded
    win.events.closing += on_closing

    def boot():
        start_tray(api)
        threading.Thread(target=api.auto_loop, daemon=True).start()
        if api.settings.get("auto_update", True):
            threading.Thread(target=lambda: (time.sleep(5), api.check_update(silent=BACKGROUND)),
                             daemon=True).start()

    webview.start(
        boot,
        gui="edgechromium" if os.name == "nt" else None,
        debug=False,
        icon=str(resource("assets/logo.ico")),
        private_mode=False,
        storage_path=str(webview_storage),
    )


if __name__ == "__main__":
    main()
