"""QASSIMZ Organizer — core engine.

Scans a folder, classifies each file (and *what kind* of photo/video it is),
builds a move/rename plan, applies it, and can undo it.
Pure Python + optional Pillow. No network, nothing leaves the PC.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import struct
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

try:
    from PIL import Image, ExifTags  # type: ignore
    _HAS_PIL = True
except Exception:  # pragma: no cover
    _HAS_PIL = False

APP_DIR_NAME = ".qassimz-organizer"

# ---------------------------------------------------------------- extensions
EXT = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif",
               ".tif", ".tiff", ".jfif", ".avif", ".ico", ".raw", ".cr2", ".nef", ".arw", ".dng"},
    "designs": {".psd", ".ai", ".svg", ".xd", ".fig", ".eps", ".indd", ".sketch", ".cdr", ".aep", ".prproj", ".mogrt"},
    "videos": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".mts", ".m2ts", ".ts", ".mpg", ".mpeg"},
    "audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".opus", ".m4a", ".wma", ".amr", ".aiff"},
    "documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".txt", ".rtf",
                  ".odt", ".ods", ".odp", ".md", ".epub", ".pages", ".numbers", ".key"},
    "programs": {".exe", ".msi", ".msix", ".appx", ".appxbundle", ".bat", ".cmd", ".apk", ".xapk", ".jar", ".reg", ".dmg"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".cab", ".tgz"},
    "code": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".xml", ".yml", ".yaml",
             ".c", ".cpp", ".h", ".cs", ".java", ".php", ".go", ".rs", ".sh", ".ps1", ".sql", ".ipynb", ".jsx"},
    "fonts": {".ttf", ".otf", ".woff", ".woff2", ".fon"},
    "torrents": {".torrent"},
}
PARTIAL = {".crdownload", ".part", ".partial", ".tmp", ".download", ".qdm", ".opdownload", ".!ut"}

# ------------------------------------------------------------- folder names
NAMES = {
    "ar": {
        "images": "صور", "designs": "تصميمات", "videos": "فيديوهات", "audio": "صوتيات",
        "documents": "مستندات", "programs": "برامج", "archives": "ملفات مضغوطة", "code": "أكواد",
        "fonts": "خطوط", "torrents": "تورنت", "others": "أخرى", "duplicates": "مكرر",
        # sub-kinds
        "screenshot": "لقطات شاشة", "whatsapp": "واتساب", "camera": "كاميرا", "wallpaper": "خلفيات",
        "graphic": "جرافيك وملصقات", "photo": "صور عامة",
        "screenrec": "تسجيلات شاشة", "shorts": "شورتس وريلز", "video": "فيديوهات عامة",
        "voice": "رسائل صوتية", "music": "موسيقى",
        "installers": "برامج تسطيب", "android": "تطبيقات أندرويد", "scripts": "سكريبتات",
        "pdf": "PDF", "word": "وورد", "excel": "إكسل", "slides": "عروض", "text": "نصوص", "ebook": "كتب",
    },
    "en": {
        "images": "Images", "designs": "Designs", "videos": "Videos", "audio": "Audio",
        "documents": "Documents", "programs": "Programs", "archives": "Archives", "code": "Code",
        "fonts": "Fonts", "torrents": "Torrents", "others": "Others", "duplicates": "Duplicates",
        "screenshot": "Screenshots", "whatsapp": "WhatsApp", "camera": "Camera", "wallpaper": "Wallpapers",
        "graphic": "Graphics", "photo": "Photos",
        "screenrec": "Screen Recordings", "shorts": "Shorts & Reels", "video": "Videos",
        "voice": "Voice Notes", "music": "Music",
        "installers": "Installers", "android": "Android Apps", "scripts": "Scripts",
        "pdf": "PDF", "word": "Word", "excel": "Excel", "slides": "Slides", "text": "Text", "ebook": "Books",
    },
}
# prefix used in the new file name
PREFIX = {
    "ar": {"screenshot": "لقطة شاشة", "whatsapp": "صورة واتساب", "camera": "صورة كاميرا",
           "wallpaper": "خلفية", "graphic": "جرافيك", "photo": "صورة",
           "screenrec": "تسجيل شاشة", "shorts": "فيديو طولي", "video": "فيديو",
           "wa_video": "فيديو واتساب", "cam_video": "فيديو كاميرا",
           "voice": "رسالة صوتية"},
    "en": {"screenshot": "Screenshot", "whatsapp": "WhatsApp Image", "camera": "Photo",
           "wallpaper": "Wallpaper", "graphic": "Graphic", "photo": "Image",
           "screenrec": "Screen Recording", "shorts": "Vertical Video", "video": "Video",
           "wa_video": "WhatsApp Video", "cam_video": "Camera Video",
           "voice": "Voice Note"},
}
COLORS = {
    "ar": {"red": "أحمر", "orange": "برتقالي", "yellow": "أصفر", "green": "أخضر", "cyan": "سماوي",
           "blue": "أزرق", "purple": "بنفسجي", "pink": "وردي", "black": "داكن", "white": "فاتح", "gray": "رمادي"},
    "en": {k: k.capitalize() for k in ["red", "orange", "yellow", "green", "cyan", "blue", "purple",
                                         "pink", "black", "white", "gray"]},
}
ORIENT = {"ar": {"portrait": "طولي", "landscape": "عرضي", "square": "مربع"},
          "en": {"portrait": "Portrait", "landscape": "Landscape", "square": "Square"}}

SCREEN_SIZES = {(1920, 1080), (1366, 768), (1536, 864), (1440, 900), (1280, 720), (1600, 900),
                (2560, 1440), (3840, 2160), (1280, 800), (1680, 1050), (1920, 1200), (2560, 1600),
                (1170, 2532), (1080, 2400), (1080, 2340), (1080, 1920), (1284, 2778), (1179, 2556),
                (1290, 2796), (720, 1600), (1440, 3200), (1080, 2408), (828, 1792), (750, 1334)}
WALL_SIZES = {(3840, 2160), (2560, 1440), (5120, 2880), (7680, 4320), (3440, 1440)}

INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class Options:
    folder: str = ""
    lang: str = "ar"              # folder + file naming language
    rename: bool = True           # smart rename images / videos / voice notes
    subkinds: bool = True         # Images/Screenshots, Videos/Shorts ...
    by_date: bool = False         # .../2026/11 for photos & videos
    recursive: bool = False
    duplicates: bool = True       # move exact duplicates to a Duplicates folder
    include_color: bool = True    # dominant color in image names
    skip_recent_minutes: int = 2  # don't touch files that are still being written


@dataclass
class Item:
    src: str
    dst: str
    category: str
    kind: str = ""
    label: str = ""               # human readable "what is it"
    size: int = 0
    duplicate: bool = False
    status: str = "pending"
    error: str = ""


@dataclass
class Plan:
    folder: str
    items: list = field(default_factory=list)
    skipped: int = 0
    stats: dict = field(default_factory=dict)


# ============================================================ metadata readers
def _exif(path: Path) -> dict:
    out: dict = {}
    if not _HAS_PIL:
        return out
    try:
        with Image.open(path) as im:
            out["w"], out["h"] = im.size
            try:
                ex = im.getexif()
                tags = {ExifTags.TAGS.get(k, k): v for k, v in ex.items()}
                try:
                    sub = ex.get_ifd(0x8769)
                    tags.update({ExifTags.TAGS.get(k, k): v for k, v in sub.items()})
                except Exception:
                    pass
                out["make"] = str(tags.get("Make", "") or "").strip("\x00 ").strip()
                out["model"] = str(tags.get("Model", "") or "").strip("\x00 ").strip()
                out["software"] = str(tags.get("Software", "") or "").strip("\x00 ")
                dt = tags.get("DateTimeOriginal") or tags.get("DateTime")
                if dt:
                    try:
                        out["date"] = _dt.datetime.strptime(str(dt).strip("\x00 ")[:19], "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
                orient = tags.get("Orientation")
                if orient in (5, 6, 7, 8):
                    out["w"], out["h"] = out["h"], out["w"]
            except Exception:
                pass
            if "w" in out:
                out["color"] = _dominant_color(im)
                out["has_alpha"] = im.mode in ("RGBA", "LA", "P") and "transparency" in im.info or im.mode == "RGBA"
    except Exception:
        pass
    return out


def _dominant_color(im) -> str:
    try:
        import colorsys
        sm = im.convert("RGB").resize((48, 48))
        px = list(sm.getdata())
        r = sum(p[0] for p in px) / len(px)
        g = sum(p[1] for p in px) / len(px)
        b = sum(p[2] for p in px) / len(px)
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l < 0.18:
            return "black"
        if l > 0.85:
            return "white"
        if s < 0.18:
            return "gray"
        deg = h * 360
        for lim, name in [(15, "red"), (40, "orange"), (65, "yellow"), (160, "green"), (195, "cyan"),
                          (255, "blue"), (290, "purple"), (335, "pink"), (361, "red")]:
            if deg < lim:
                return name
    except Exception:
        pass
    return ""


def _mp4_meta(path: Path) -> dict:
    """Tiny ISO-BMFF reader: duration, creation date, width/height. No ffmpeg needed."""
    out: dict = {}
    try:
        size_total = path.stat().st_size
        with open(path, "rb") as f:
            def boxes(start, end):
                pos = start
                while pos + 8 <= end:
                    f.seek(pos)
                    hdr = f.read(8)
                    if len(hdr) < 8:
                        return
                    sz, typ = struct.unpack(">I4s", hdr)
                    hl = 8
                    if sz == 1:
                        sz = struct.unpack(">Q", f.read(8))[0]
                        hl = 16
                    elif sz == 0:
                        sz = end - pos
                    if sz < hl:
                        return
                    yield typ, pos + hl, pos + sz
                    pos += sz

            for typ, s, e in boxes(0, size_total):
                if typ != b"moov":
                    continue
                dims = []
                for t2, s2, e2 in boxes(s, e):
                    if t2 == b"mvhd":
                        f.seek(s2)
                        ver = f.read(1)[0]
                        f.read(3)
                        if ver == 1:
                            ctime, _m, scale, dur = struct.unpack(">QQIQ", f.read(28))
                        else:
                            ctime, _m, scale, dur = struct.unpack(">IIII", f.read(16))
                        if scale:
                            out["duration"] = dur / scale
                        if ctime > 0:
                            d = _dt.datetime(1904, 1, 1) + _dt.timedelta(seconds=ctime)
                            if 1990 < d.year <= _dt.datetime.now().year + 1:
                                out["date"] = d
                    elif t2 == b"trak":
                        for t3, s3, e3 in boxes(s2, e2):
                            if t3 == b"tkhd":
                                f.seek(e3 - 8)
                                w, h = struct.unpack(">II", f.read(8))
                                w, h = w >> 16, h >> 16
                                if w and h:
                                    # rotation matrix (a, b) tells portrait recordings
                                    f.seek(e3 - 8 - 36)
                                    a, b = struct.unpack(">ii", f.read(8))
                                    if a == 0 and b != 0:
                                        w, h = h, w
                                    dims.append((w, h))
                if dims:
                    out["w"], out["h"] = max(dims, key=lambda d: d[0] * d[1])
                break
    except Exception:
        pass
    return out


# ================================================================ classifying
def _category(ext: str) -> str:
    for cat, exts in EXT.items():
        if ext in exts:
            return cat
    return "others"


def _file_date(p: Path, meta: dict) -> _dt.datetime:
    if meta.get("date"):
        return meta["date"]
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_ ]?(\d{2})?[-_.]?(\d{2})?[-_.]?(\d{2})?", p.stem)
    if m:
        try:
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
            hh, mm, ss = int(m[4] or 0), int(m[5] or 0), int(m[6] or 0)
            if hh > 23 or mm > 59 or ss > 59:
                hh = mm = ss = 0
            return _dt.datetime(y, mo, d, hh, mm, ss)
        except ValueError:
            pass
    st = p.stat()
    return _dt.datetime.fromtimestamp(min(st.st_mtime, getattr(st, "st_ctime", st.st_mtime)))


def _image_kind(p: Path, meta: dict) -> str:
    n = p.name.lower()
    w, h = meta.get("w", 0), meta.get("h", 0)
    if re.search(r"screenshot|screen ?shot|لقطة|snip|capture|scr_", n):
        return "screenshot"
    if re.search(r"-wa\d{3,}|whatsapp", n):
        return "whatsapp"
    if meta.get("make") or meta.get("model") or re.match(r"(img|dsc|pxl|dji|gopr)[_-]?\d", n):
        return "camera"
    if p.suffix.lower() == ".png" and ((w, h) in SCREEN_SIZES or (h, w) in SCREEN_SIZES):
        return "screenshot"
    if (w, h) in WALL_SIZES or "wallpaper" in n:
        return "wallpaper"
    if p.suffix.lower() in {".png", ".gif", ".webp", ".svg", ".ico"} and (meta.get("has_alpha") or max(w, h) <= 1200):
        return "graphic"
    return "photo"


def _video_kind(p: Path, meta: dict) -> str:
    n = p.name.lower()
    w, h = meta.get("w", 0), meta.get("h", 0)
    if re.search(r"screen ?record|recording|obs|bandicam|capture|تسجيل", n):
        return "screenrec"
    if re.search(r"-wa\d{3,}|whatsapp", n):
        return "wa_video"
    if h and w and h > w * 1.2:
        return "shorts"
    if re.match(r"(vid|mov|pxl|dji|gopr|dsc|mvi)[_-]?\d", n):
        return "cam_video"
    return "video"


def _video_folder_kind(kind: str) -> str:
    return {"wa_video": "whatsapp", "cam_video": "camera"}.get(kind, kind)


def _res_label(w: int, h: int) -> str:
    s = min(w, h)
    if not s:
        return ""
    if s >= 2100:
        return "4K"
    if s >= 1400:
        return "2K"
    if s >= 1000:
        return "1080p"
    if s >= 700:
        return "720p"
    return f"{s}p"


def _dur_label(sec: float, lang: str) -> str:
    sec = int(round(sec))
    m, s = divmod(sec, 60)
    hr, m = divmod(m, 60)
    if hr:
        return f"{hr}h{m:02d}m"
    return f"{m}m{s:02d}s" if m else f"{s}s"


def _orient(w, h):
    if not w or not h:
        return ""
    if abs(w - h) / max(w, h) < 0.05:
        return "square"
    return "portrait" if h > w else "landscape"


def _clean(name: str) -> str:
    name = INVALID.sub("", name).strip(" .")
    return re.sub(r"\s+", " ", name)[:150] or "file"


def _sub_for_doc(ext: str) -> str:
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx", ".odt", ".rtf", ".pages"}:
        return "word"
    if ext in {".xls", ".xlsx", ".csv", ".ods", ".numbers"}:
        return "excel"
    if ext in {".ppt", ".pptx", ".odp", ".key"}:
        return "slides"
    if ext == ".epub":
        return "ebook"
    return "text"


def describe(p: Path, opt: Options) -> tuple[str, str, str, str]:
    """-> (category, kind, relative_folder, new_file_name)"""
    L = opt.lang if opt.lang in NAMES else "ar"
    N, P = NAMES[L], PREFIX[L]
    ext = p.suffix.lower()
    cat = _category(ext)
    folder = [N[cat]]
    new_name = p.name
    kind = ""
    meta: dict = {}

    if cat == "images":
        meta = _exif(p)
        kind = _image_kind(p, meta)
        if opt.subkinds:
            folder.append(N[kind])
        d = _file_date(p, meta)
        if opt.by_date and kind in ("camera", "whatsapp", "photo", "screenshot"):
            folder += [f"{d:%Y}", f"{d:%m}"]
        if opt.rename:
            parts = [P[kind], f"{d:%Y-%m-%d}", f"{d:%H-%M-%S}"]
            if kind == "camera" and meta.get("model"):
                parts.append(meta["model"].replace(meta.get("make", ""), "").strip() or meta["model"])
            o = _orient(meta.get("w", 0), meta.get("h", 0))
            if o and kind not in ("screenshot",):
                parts.append(ORIENT[L][o])
            if opt.include_color and meta.get("color") and kind in ("photo", "graphic", "wallpaper", "camera"):
                parts.append(COLORS[L][meta["color"]])
            if kind == "screenshot" and meta.get("w"):
                parts.append(f"{meta['w']}x{meta['h']}")
            new_name = _clean(" ".join(parts[:1]) + "_" + "_".join(parts[1:])) + ext
    elif cat == "videos":
        meta = _mp4_meta(p) if ext in {".mp4", ".mov", ".m4v", ".3gp"} else {}
        kind = _video_kind(p, meta)
        if opt.subkinds:
            folder.append(N[_video_folder_kind(kind)])
        d = _file_date(p, meta)
        if opt.by_date and kind in ("cam_video", "wa_video"):
            folder += [f"{d:%Y}", f"{d:%m}"]
        if opt.rename:
            parts = [P[kind], f"{d:%Y-%m-%d}", f"{d:%H-%M-%S}"]
            r = _res_label(meta.get("w", 0), meta.get("h", 0))
            if r:
                parts.append(r)
            if meta.get("duration"):
                parts.append(_dur_label(meta["duration"], L))
            new_name = _clean(parts[0] + "_" + "_".join(parts[1:])) + ext
    elif cat == "audio":
        n = p.name.lower()
        kind = "voice" if (re.search(r"ptt-|aud-.*-wa|voice|recording|تسجيل", n) or ext in {".opus", ".amr"}) else "music"
        if opt.subkinds:
            folder.append(N[kind])
        if opt.rename and kind == "voice":
            d = _file_date(p, meta)
            new_name = _clean(f"{P['voice']}_{d:%Y-%m-%d}_{d:%H-%M-%S}") + ext
    elif cat == "documents":
        kind = _sub_for_doc(ext)
        if opt.subkinds:
            folder.append(N[kind])
    elif cat == "programs":
        kind = "android" if ext in {".apk", ".xapk"} else "scripts" if ext in {".bat", ".cmd", ".reg"} else "installers"
        if opt.subkinds:
            folder.append(N[kind])
    return cat, kind, os.path.join(*folder), new_name


# ===================================================================== plan
def _iter_files(root: Path, recursive: bool, own_dirs: set):
    if not recursive:
        for e in os.scandir(root):
            if e.is_file(follow_symlinks=False):
                yield Path(e.path)
        return
    for dp, dns, fns in os.walk(root):
        rel = Path(dp).relative_to(root)
        if rel.parts and rel.parts[0] in own_dirs:
            dns[:] = []
            continue
        dns[:] = [d for d in dns if not d.startswith(".") and not (Path(dp) == root and d in own_dirs)]
        for fn in fns:
            yield Path(dp) / fn


def _hash(p: Path) -> str:
    h = hashlib.blake2b(digest_size=20)
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_plan(opt: Options, progress=None) -> Plan:
    root = Path(opt.folder).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(opt.folder)
    own = set(NAMES["ar"].values()) | set(NAMES["en"].values()) | {APP_DIR_NAME}
    files = []
    skipped = 0
    now = time.time()
    for p in _iter_files(root, opt.recursive, own):
        n = p.name
        if n.startswith(".") or n.lower() in {"desktop.ini", "thumbs.db"} or p.suffix.lower() in PARTIAL:
            skipped += 1
            continue
        try:
            if now - p.stat().st_mtime < opt.skip_recent_minutes * 60:
                skipped += 1
                continue
        except OSError:
            skipped += 1
            continue
        files.append(p)

    plan = Plan(folder=str(root), skipped=skipped)
    taken: set = set()
    by_size: dict = {}
    total = len(files)
    for i, p in enumerate(files):
        if progress:
            progress(i + 1, total, p.name)
        try:
            cat, kind, rel, name = describe(p, opt)
            size = p.stat().st_size
        except Exception as ex:  # unreadable file
            plan.items.append(asdict(Item(str(p), str(p), "others", status="error", error=str(ex))))
            continue
        dup = False
        if opt.duplicates and size > 0:
            by_size.setdefault(size, []).append(p)
            if len(by_size[size]) > 1:
                try:
                    hp = _hash(p)
                    for q in by_size[size][:-1]:
                        if _hash_cached(q) == hp:
                            dup = True
                            break
                    _HCACHE[str(p)] = hp
                except OSError:
                    pass
        if dup:
            rel = NAMES[opt.lang if opt.lang in NAMES else "ar"]["duplicates"]
            name = p.name
        dst = root / rel / name
        dst = _unique(dst, taken, p)
        taken.add(str(dst).lower())
        label = NAMES[opt.lang if opt.lang in NAMES else "ar"].get(kind, "") or NAMES[opt.lang if opt.lang in NAMES else "ar"][cat]
        plan.items.append(asdict(Item(str(p), str(dst), cat, kind, label, size, dup)))
        plan.stats[cat] = plan.stats.get(cat, 0) + 1
    if opt.duplicates:
        plan.stats["duplicates"] = sum(1 for it in plan.items if it["duplicate"])
    _HCACHE.clear()
    return plan


_HCACHE: dict = {}


def _hash_cached(p: Path) -> str:
    k = str(p)
    if k not in _HCACHE:
        _HCACHE[k] = _hash(p)
    return _HCACHE[k]


def _unique(dst: Path, taken: set, src: Path) -> Path:
    if dst.resolve() == src.resolve() if dst.exists() else False:
        return dst
    stem, ext = dst.stem, dst.suffix
    cand, n = dst, 2
    while str(cand).lower() in taken or (cand.exists() and cand.resolve() != src.resolve()):
        cand = dst.with_name(f"{stem} ({n}){ext}")
        n += 1
    return cand


# ==================================================================== apply
def apply_plan(plan: dict, progress=None) -> dict:
    root = Path(plan["folder"])
    log_dir = root / APP_DIR_NAME
    log_dir.mkdir(exist_ok=True)
    try:  # hide the log folder on Windows
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(log_dir), 0x02)
    except Exception:
        pass
    done, errors = [], 0
    items = plan["items"]
    for i, it in enumerate(items):
        if progress:
            progress(i + 1, len(items), Path(it["src"]).name)
        if it.get("status") == "error" or it["src"] == it["dst"]:
            continue
        try:
            dst = Path(it["dst"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = _unique(dst, set(), Path(it["src"]))
            shutil.move(it["src"], dst)
            it["dst"] = str(dst)
            it["status"] = "done"
            done.append({"src": it["src"], "dst": str(dst)})
        except Exception as ex:
            it["status"] = "error"
            it["error"] = str(ex)
            errors += 1
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    if done:
        (log_dir / f"history-{stamp}.json").write_text(
            json.dumps({"folder": str(root), "time": stamp, "moves": done}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    return {"moved": len(done), "errors": errors, "items": items}


def history(folder: str) -> list:
    d = Path(folder) / APP_DIR_NAME
    if not d.is_dir():
        return []
    return sorted((p.name for p in d.glob("history-*.json")), reverse=True)


def undo_last(folder: str) -> dict:
    d = Path(folder) / APP_DIR_NAME
    logs = sorted(d.glob("history-*.json")) if d.is_dir() else []
    if not logs:
        return {"restored": 0, "errors": 0, "message": "no-history"}
    log = logs[-1]
    data = json.loads(log.read_text(encoding="utf-8"))
    restored = errors = 0
    for mv in reversed(data["moves"]):
        try:
            src, dst = Path(mv["src"]), Path(mv["dst"])
            if dst.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
                restored += 1
                _rm_empty(dst.parent, Path(folder))
        except Exception:
            errors += 1
    log.rename(log.with_suffix(".undone"))
    return {"restored": restored, "errors": errors}


def _rm_empty(d: Path, stop: Path):
    try:
        while d != stop and d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent
    except OSError:
        pass
