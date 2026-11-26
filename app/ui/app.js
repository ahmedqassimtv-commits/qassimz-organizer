/* QASSIMZ Organizer v1.1.0 — Architectural File Blueprint Studio UI */
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const CAT = {
  images: ["🖼️", "صور"], designs: ["🎨", "تصميمات"], videos: ["🎬", "فيديوهات"], audio: ["🎵", "صوتيات"],
  documents: ["📄", "مستندات"], programs: ["💿", "برامج"], archives: ["🗜️", "مضغوط"], code: ["⌨️", "أكواد"],
  fonts: ["🔤", "خطوط"], torrents: ["🧲", "تورنت"], others: ["📦", "أخرى"], duplicates: ["♊", "مكرر"],
};

let INFO = { github: "#", support: "#", site: "https://qassimz.com", downloads: "" };
let S = {};
let state = { folder: "", lang: "ar", plan: null, excluded: new Set(), filter: "", search: "", page: "organize", isBusy: false };

/* ---------- backend bridge (pywebview) + browser demo fallback ---------- */
const api = () => (window.pywebview && window.pywebview.api) || demoApi;

const demoApi = {
  info: async () => ({
    name: "QASSIMZ Organizer",
    version: "1.1.0",
    github: "https://github.com/ahmedqassimtv-commits/qassimz-organizer",
    support: "https://github.com/ahmedqassimtv-commits/qassimz-organizer/issues",
    site: "https://qassimz.com",
    downloads: "C:\\Users\\Ahmed\\Downloads",
  }),
  load_settings: async () => Object.assign(
    { auto: false, auto_folders: ["C:\\Users\\Ahmed\\Downloads"], auto_interval: 10, auto_update: true },
    JSON.parse(localStorageSafe("qz") || "{}")
  ),
  save_settings: async (s) => { try { localStorage.setItem("qz", JSON.stringify(s)); } catch (e) {} return true; },
  pick_folder: async () => "C:\\Users\\Ahmed\\Downloads",
  open_url: async (u) => window.open(u, "_blank"),
  open_folder: async () => {},
  open_readme: async () => {},
  history: async () => ["history-20261125-184648.json"],
  set_startup: async (on) => on,
  organize_now: async () => { setTimeout(() => window.onBackend("auto", { moved: 7, at: "2026-11-25 18:55" }), 600); return true; },
  check_update: async () => { const u = { version: "1.2.0", url: "#", notes: "تحسينات في السرعة ودعم صيغ إضافية" }; window.onBackend("update", u); return u; },
  install_update: async () => { let p = 0; const t = setInterval(() => { p += 10; window.onBackend("update_progress", p); if (p >= 100) clearInterval(t); }, 120); return true; },
  undo: async () => ({ restored: 12, errors: 0 }),
  scan: async () => {
    const F = "C:\\Users\\Ahmed\\Downloads\\";
    const demo = [
      ["IMG_20261102_141233.jpg", "صور\\كاميرا\\صورة كاميرا_2026-11-02_14-12-33_SM-S918B_طولي_أزرق.jpg", "images", "كاميرا", false, 4820190],
      ["Screenshot 2026-11-20 101500.png", "صور\\لقطات شاشة\\لقطة شاشة_2026-11-20_10-15-00_1920x1080.png", "images", "لقطات شاشة", false, 1290400],
      ["IMG-20261111-WA0007.jpg", "صور\\واتساب\\صورة واتساب_2026-11-11_00-00-00_مربع.jpg", "images", "واتساب", false, 342100],
      ["reel_final.mp4", "فيديوهات\\شورتس وريلز\\فيديو طولي_2026-11-19_20-41-10_1080p_58s.mp4", "videos", "شورتس وريلز", false, 48500200],
      ["2026-11-18 21-03-55.mkv", "فيديوهات\\تسجيلات شاشة\\تسجيل شاشة_2026-11-18_21-03-55.mkv", "videos", "تسجيلات شاشة", false, 184200000],
      ["ChromeSetup.exe", "برامج\\برامج تسطيب\\ChromeSetup.exe", "programs", "برامج تسطيب", false, 1120400],
      ["PTT-20261101-WA0003.opus", "صوتيات\\رسائل صوتية\\رسالة صوتية_2026-11-01_00-00-00.opus", "audio", "رسائل صوتية", false, 98400],
      ["Invoice.pdf", "مستندات\\PDF\\Invoice.pdf", "documents", "PDF", false, 512000],
      ["QASSIMZ_logo.psd", "تصميمات\\QASSIMZ_logo.psd", "designs", "تصميمات", false, 36900000],
      ["fonts-pack.zip", "ملفات مضغوطة\\fonts-pack.zip", "archives", "ملفات مضغوطة", false, 14800000],
      ["IMG_20261102_141233 (1).jpg", "مكرر\\IMG_20261102_141233 (1).jpg", "images", "كاميرا", true, 4820190],
    ];
    let i = 0;
    const tick = setInterval(() => {
      i++;
      window.onBackend("progress", { i, n: demo.length, name: demo[i - 1][0], phase: "scan" });
      if (i >= demo.length) {
        clearInterval(tick);
        const items = demo.map(([s, d, c, l, dup, sz]) => ({ src: F + s, dst: F + d, category: c, label: l, duplicate: !!dup, size: sz }));
        const stats = {};
        items.forEach((x) => { if (!x.duplicate) stats[x.category] = (stats[x.category] || 0) + 1; });
        stats.duplicates = 1;
        window.onBackend("plan", { folder: F.slice(0, -1), items, skipped: 2, stats });
      }
    }, 65);
    return true;
  },
  apply: async () => { setTimeout(() => window.onBackend("applied", { moved: 11, errors: 0, folder: state.folder }), 600); return true; },
};

function localStorageSafe(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const base = (p) => p.split(/[\\/]/).pop();
const rel = (p) => { const f = state.plan.folder; return p.startsWith(f) ? p.slice(f.length + 1) : p; };
const fmtSize = (n) => {
  if (!n || n <= 0) return "—";
  if (n < 1024) return n + " B";
  if (n < 1048576) return (n / 1024).toFixed(0) + " KB";
  if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB";
  return (n / 1073741824).toFixed(2) + " GB";
};

/* ---------- events from Python ---------- */
window.onBackend = (ev, d) => {
  if (ev === "progress") {
    $("#progCard").classList.remove("hidden");
    $("#progTitle").textContent = d.phase === "scan" ? "بيفحص الملفات…" : "بينقل ويسمّي…";
    $("#progNum").textContent = `${d.i} / ${d.n}`;
    $("#progBar").style.width = (d.n ? (d.i / d.n) * 100 : 0) + "%";
    $("#progName").textContent = d.name;
  } else if (ev === "plan") {
    $("#progCard").classList.add("hidden");
    busy(false);
    showPlan(d);
  } else if (ev === "applied") {
    $("#progCard").classList.add("hidden");
    $("#resultCard").classList.add("hidden");
    $("#emptyState").classList.remove("hidden");
    state.plan = null;
    busy(false);
    toast(`✓ اتنقل ${d.moved} ملف${d.errors ? ` — ${d.errors} مشكلة` : ""}`, [
      ["افتح المجلد", () => api().open_folder(d.folder)],
      ["تراجع", doUndo],
    ]);
  } else if (ev === "open_folder") {
    if (d) {
      $("#welcome").classList.add("hidden");
      go("organize");
      setFolder(d);
      state.plan = null;
      $("#resultCard").classList.add("hidden");
      $("#emptyState").classList.remove("hidden");
    }
  } else if (ev === "auto") {
    S.last_auto = d.at;
    renderAuto();
    if (d.moved) toast(`⚡ اترتب ${d.moved} ملف تلقائياً`);
  } else if (ev === "settings") {
    Object.assign(S, d);
    renderAuto();
  } else if (ev === "update") {
    showUpdate(d);
  } else if (ev === "update_progress") {
    $("#updBar").style.width = d + "%";
    $("#btnUpdate").textContent = `بيحمّل… ${d}%`;
  } else if (ev === "error") {
    $("#progCard").classList.add("hidden");
    busy(false);
    toast("⚠️ " + d);
  }
};

/* ---------- UI ---------- */
function busy(b) {
  state.isBusy = b;
  ["#btnScan", "#btnApply", "#btnPick"].forEach((s) => { const el = $(s); if (el) el.disabled = b; });
}

function setFolder(p) {
  state.folder = p || "";
  $("#folderPath").textContent = p || "اختار مجلد…";
  $("#histPath").textContent = p || "—";
  persist();
}

function opts() {
  const o = { folder: state.folder, lang: state.lang };
  ["rename", "subkinds", "duplicates", "by_date", "recursive", "include_color"].forEach((k) => {
    o[k] = $("#o_" + k).checked;
  });
  return o;
}

function persist() {
  const o = opts();
  delete o.folder;
  Object.assign(S, o, { folder: state.folder, welcomed: true });
  api().save_settings(S);
}

function renderAuto() {
  $("#a_auto").checked = !!S.auto;
  $("#autoDot").classList.toggle("on", !!S.auto);
  $("#autoStatus").textContent = S.auto
    ? `شغّال — كل ${S.auto_interval >= 60 ? "ساعة" : S.auto_interval + " دقيقة"}${S.last_auto ? ` · آخر ترتيب ${S.last_auto}` : ""}`
    : "مقفول — شغّله والبرنامج هيرتب لوحده";
  $("#a_update").checked = S.auto_update !== false;
  $$("#intSeg button").forEach((b) => b.classList.toggle("on", +b.dataset.v === +S.auto_interval));
  const f = S.auto_folders || [];
  $("#autoFolders").innerHTML = f.length
    ? f.map((p, i) => `<li><span class="f-ic">📁</span><span dir="ltr" title="${esc(p)}">${esc(p)}</span><button data-i="${i}" type="button" title="إزالة">✕</button></li>`).join("")
    : `<li class="muted">مفيش مجلدات — ضيف التنزيلات مثلاً</li>`;
  $$("#autoFolders button").forEach((b) => {
    b.onclick = () => {
      S.auto_folders.splice(+b.dataset.i, 1);
      api().save_settings(S);
      renderAuto();
    };
  });
}

function showUpdate(u) {
  INFO.update = u;
  $("#updPill").classList.remove("hidden");
  $("#updVer").textContent = "v" + u.version;
  $("#updBox").classList.remove("hidden");
  $("#updVer2").textContent = "v" + u.version;
  $("#updNotes").textContent = u.notes || "";
}

function showPlan(plan) {
  state.plan = plan;
  state.excluded = new Set();
  state.filter = "";
  state.search = "";
  $("#search").value = "";
  $("#chkAll").checked = true;
  $("#emptyState").classList.add("hidden");
  $("#resultCard").classList.remove("hidden");

  const n = plan.items.filter((x) => x.status !== "error").length;
  $("#resTitle").textContent = n ? `${n} ملف جاهز للترتيب` : "المجلد مترتب بالكامل 👌";
  $("#resSub").textContent = plan.skipped
    ? `تم تخطي ${plan.skipped} ملف (مخفي / قيد التحميل / اتعدل حالاً)`
    : "أزل علامة ✓ من أي ملف لا تريد تحريكه — أو اضغط Ctrl+Enter للتنفيذ";

  const chips = [`<span class="chip on" data-c="">الكل<b>${n}</b></span>`];
  Object.entries(plan.stats).forEach(([c, v]) => {
    if (v && CAT[c]) chips.push(`<span class="chip" data-c="${c}">${CAT[c][0]} ${CAT[c][1]}<b>${v}</b></span>`);
  });
  $("#chips").innerHTML = chips.join("");
  $$("#chips .chip").forEach((el) => {
    el.onclick = () => {
      $$("#chips .chip").forEach((x) => x.classList.remove("on"));
      el.classList.add("on");
      state.filter = el.dataset.c;
      renderRows();
    };
  });
  renderRows();
}

function renderRows() {
  if (!state.plan) return;
  const q = state.search.toLowerCase();
  const items = state.plan.items.filter((it) =>
    it.status !== "error" &&
    (!state.filter || (state.filter === "duplicates" ? it.duplicate : it.category === state.filter && !it.duplicate)) &&
    (!q || it.src.toLowerCase().includes(q) || it.dst.toLowerCase().includes(q))
  );
  const max = 1500;
  $("#rows").innerHTML = items.slice(0, max).map((it) => {
    const r = rel(it.dst);
    const parts = r.split(/[\\/]/);
    const file = parts.pop();
    const folderTrail = parts.join(" / ");
    const off = state.excluded.has(it.src);
    const ic = it.duplicate ? CAT.duplicates[0] : (CAT[it.category] || CAT.others)[0];
    return `<tr class="${off ? "off" : ""}" data-s="${esc(it.src)}">
      <td><input type="checkbox" ${off ? "" : "checked"}></td>
      <td class="src" title="${esc(it.src)}"><span class="src-name" dir="ltr">${esc(base(it.src))}</span></td>
      <td><span class="k ${it.duplicate ? "dup" : ""}">${ic} ${esc(it.duplicate ? "مكرر" : it.label || "")}</span></td>
      <td class="dst" title="${esc(r)}">
        <div class="bp-target">
          ${folderTrail ? `<span class="bp-folders ${it.duplicate ? "dup" : ""}" dir="auto">${esc(folderTrail)}</span><span class="bp-sep">‹</span>` : ""}
          <span class="bp-file" dir="auto">${esc(file)}</span>
        </div>
      </td>
      <td class="sz">${fmtSize(it.size)}</td>
    </tr>`;
  }).join("") + (items.length > max ? `<tr><td colspan="5" class="muted">… و ${items.length - max} ملف إضافي</td></tr>` : "");

  $$("#rows tr[data-s]").forEach((tr) => {
    tr.querySelector("input").onchange = (e) => {
      const s = tr.dataset.s;
      e.target.checked ? state.excluded.delete(s) : state.excluded.add(s);
      tr.classList.toggle("off", !e.target.checked);
      count();
    };
  });
  count();
}

function count() {
  if (!state.plan) return;
  const n = state.plan.items.filter((x) => x.status !== "error").length - state.excluded.size;
  $("#btnApply").innerHTML = `✓ نفّذ الترتيب (${n}) <kbd>Ctrl+↵</kbd>`;
  $("#btnApply").disabled = n <= 0 || state.isBusy;
}

let toastT;
function toast(msg, actions = []) {
  $("#toastMsg").textContent = msg;
  $("#toastAct").innerHTML = "";
  actions.forEach(([t, fn]) => {
    const b = document.createElement("button");
    b.className = "btn ghost";
    b.type = "button";
    b.textContent = t;
    b.onclick = () => { fn(); hideToast(); };
    $("#toastAct").appendChild(b);
  });
  $("#toast").classList.remove("hidden");
  clearTimeout(toastT);
  toastT = setTimeout(hideToast, actions.length ? 12000 : 4000);
}
const hideToast = () => $("#toast").classList.add("hidden");

async function doUndo() {
  if (!state.folder) return toast("اختار المجلد الأول");
  const r = await api().undo(state.folder);
  if (!r || r.message === "no-history") return toast("مفيش عمليات ترتيب مسجلة في المجلد ده");
  toast(`↺ رجعنا ${r.restored} ملف مكانه${r.errors ? ` — ${r.errors} مشكلة` : ""}`);
  loadHistory();
}

async function loadHistory() {
  const list = state.folder ? await api().history(state.folder) : [];
  $("#histList").innerHTML = list.length
    ? list.map((h) => {
        const m = h.match(/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})/);
        return `<li><span>ترتيب بتاريخ ${m ? `${m[3]}/${m[2]}/${m[1]} — ${m[4]}:${m[5]}` : esc(h)}</span><span class="hist-badge">قابل للتراجع</span></li>`;
      }).join("")
    : `<li class="muted">مفيش سجل للمجلد ده لسه.</li>`;
}

function go(page) {
  state.page = page;
  $$(".nav").forEach((n) => n.classList.toggle("active", n.dataset.page === page));
  $$(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
  if (page === "history") loadHistory();
}

async function triggerScan() {
  if (state.isBusy) return;
  if (!state.folder) return toast("اختار مجلد الأول");
  if (state.page !== "organize") go("organize");
  busy(true);
  $("#resultCard").classList.add("hidden");
  $("#progBar").style.width = "0%";
  const ok = await api().scan(opts());
  if (!ok) busy(false);
}

/* ---------- Universal e.code Keyboard Shortcuts (Arabic & English Layouts) ---------- */
function setupKeyboardShortcuts() {
  const PAGES = { Digit1: "organize", Digit2: "auto", Digit3: "history", Digit4: "about", Digit5: "guide" };

  document.addEventListener("keydown", (e) => {
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    const inText = tag === "INPUT" && document.activeElement.type !== "checkbox";
    const ctrl = e.ctrlKey || e.metaKey;
    const welcomeOpen = !$("#welcome").classList.contains("hidden");

    // Escape: close welcome/modals or clear search or dismiss toast
    if (e.code === "Escape") {
      if (welcomeOpen) {
        e.preventDefault();
        $("#welcome").classList.add("hidden");
        persist();
        return;
      }
      if (document.activeElement === $("#search") || state.search) {
        e.preventDefault();
        $("#search").value = "";
        state.search = "";
        renderRows();
        $("#search").blur();
        return;
      }
      if (!$("#toast").classList.contains("hidden")) {
        e.preventDefault();
        hideToast();
        return;
      }
    }

    if (welcomeOpen) return;

    // Ctrl+KeyO: Choose folder
    if (ctrl && !e.shiftKey && !e.altKey && e.code === "KeyO") {
      e.preventDefault();
      if (state.page === "history") $("#btnHistPick").click();
      else $("#btnPick").click();
      return;
    }

    // Ctrl+KeyF or Slash: Focus preview search #search
    if ((ctrl && !e.shiftKey && !e.altKey && e.code === "KeyF") || (!inText && !ctrl && !e.altKey && !e.shiftKey && e.code === "Slash")) {
      if (!$("#resultCard").classList.contains("hidden")) {
        e.preventDefault();
        if (state.page !== "organize") go("organize");
        const s = $("#search");
        s.focus();
        s.select();
      } else if (ctrl && e.code === "KeyF") {
        e.preventDefault();
      }
      return;
    }

    // Ctrl+KeyZ: Undo last organize operation
    if (ctrl && !e.shiftKey && !e.altKey && e.code === "KeyZ" && !inText) {
      e.preventDefault();
      doUndo();
      return;
    }

    // F5 or Ctrl+KeyR: Rescan / preview current folder
    if (e.code === "F5" || (ctrl && !e.shiftKey && !e.altKey && e.code === "KeyR")) {
      e.preventDefault();
      if (state.page === "history") loadHistory();
      else triggerScan();
      return;
    }

    // Ctrl+Enter: Execute organize when preview is ready
    if (ctrl && (e.code === "Enter" || e.code === "NumpadEnter")) {
      if (state.page === "organize" && !$("#resultCard").classList.contains("hidden") && !$("#btnApply").disabled) {
        e.preventDefault();
        $("#btnApply").click();
      }
      return;
    }

    // Digit1..Digit4 (+ Digit5): Switch tabs outside inputs
    if (!inText && !ctrl && !e.altKey && !e.shiftKey && PAGES[e.code]) {
      e.preventDefault();
      go(PAGES[e.code]);
    }
  });
}

/* ---------- wiring ---------- */
async function init() {
  INFO = await api().info();
  $("#ver").textContent = "v" + INFO.version;
  $("#aboutVer").textContent = "الإصدار " + INFO.version;

  const s = (await api().load_settings()) || {};
  S = s;
  ["rename", "subkinds", "duplicates", "by_date", "recursive", "include_color"].forEach((k) => {
    if (k in s) $("#o_" + k).checked = !!s[k];
  });
  if (s.lang) {
    state.lang = s.lang;
    $$("#langSeg button").forEach((b) => b.classList.toggle("on", b.dataset.v === s.lang));
  }
  setFolder(INFO.start_folder || s.folder || INFO.downloads);
  if (!s.welcomed && !INFO.start_folder) $("#welcome").classList.remove("hidden");

  $$(".nav").forEach((n) => (n.onclick = () => go(n.dataset.page)));
  $("#btnPick").onclick = async () => { const p = await api().pick_folder(); if (p) setFolder(p); };
  $("#btnHistPick").onclick = async () => { const p = await api().pick_folder(); if (p) { setFolder(p); loadHistory(); } };
  $("#btnDownloads").onclick = () => setFolder(INFO.downloads);
  $("#btnDesktop").onclick = () => setFolder(INFO.desktop || INFO.downloads.replace(/Downloads$/i, "Desktop"));
  $("#btnOpenCurrent").onclick = () => { if (state.folder) api().open_folder(state.folder); };

  $$("#page-organize .tog input").forEach((i) => (i.onchange = persist));
  $$("#langSeg button").forEach((b) => (b.onclick = () => {
    state.lang = b.dataset.v;
    $$("#langSeg button").forEach((x) => x.classList.toggle("on", x === b));
    persist();
  }));

  $("#btnScan").onclick = triggerScan;
  $("#btnApply").onclick = async () => { busy(true); await api().apply([...state.excluded]); };
  $("#btnCancel").onclick = () => { $("#resultCard").classList.add("hidden"); $("#emptyState").classList.remove("hidden"); };
  $("#chkAll").onchange = (e) => {
    $$("#rows tr[data-s]").forEach((tr) => {
      const s = tr.dataset.s;
      e.target.checked ? state.excluded.delete(s) : state.excluded.add(s);
      tr.classList.toggle("off", !e.target.checked);
      tr.querySelector("input").checked = e.target.checked;
    });
    count();
  };
  $("#search").oninput = (e) => { state.search = e.target.value; renderRows(); };
  $("#btnUndo").onclick = doUndo;

  renderAuto();
  $("#a_startup").checked = !!INFO.startup;
  if (INFO.update) showUpdate(INFO.update);

  $("#a_auto").onchange = (e) => {
    S.auto = e.target.checked;
    if (S.auto && !(S.auto_folders || []).length) S.auto_folders = [INFO.downloads];
    api().save_settings(S);
    renderAuto();
    if (S.auto) toast("⚡ الترتيب التلقائي اشتغل — تقدر تقفل النافذة وهو هيكمل");
  };
  $("#a_update").onchange = (e) => { S.auto_update = e.target.checked; api().save_settings(S); };
  $("#a_startup").onchange = async (e) => {
    const r = await api().set_startup(e.target.checked);
    if (r && r.error) { toast("⚠️ " + r.error); e.target.checked = !e.target.checked; }
  };
  $$("#intSeg button").forEach((b) => (b.onclick = () => {
    S.auto_interval = +b.dataset.v;
    api().save_settings(S);
    renderAuto();
  }));
  $("#btnAddFolder").onclick = async () => {
    const p = await api().pick_folder();
    if (p && !(S.auto_folders ||= []).includes(p)) {
      S.auto_folders.push(p);
      api().save_settings(S);
      renderAuto();
    }
  };
  $("#btnNow").onclick = () => { api().organize_now(); toast("⚡ بيرتب دلوقتي…"); };
  $("#updPill").onclick = () => go("about");
  $("#btnUpdate").onclick = () => { $("#btnUpdate").disabled = true; api().install_update(); };
  $("#btnCheckUpd").onclick = async () => {
    const r = await api().check_update();
    if (r && r.latest) toast("✓ عندك أحدث إصدار");
    else if (r && r.error) toast("مقدرتش أوصل للخادم دلوقتي");
  };
  $("#btnWelcome").onclick = () => { $("#welcome").classList.add("hidden"); persist(); };
  $("#btnReadme").onclick = () => api().open_readme();
  [["#btnGithub", "github"], ["#btnGithub2", "github"], ["#btnSupport", "support"], ["#btnSupport2", "support"], ["#btnSite", "site"]]
    .forEach(([sel, k]) => ($(sel).onclick = () => api().open_url(INFO[k])));

  // Folder dropzone visual support
  const dropCard = $("#folderDropCard");
  if (dropCard) {
    dropCard.addEventListener("dragover", (e) => { e.preventDefault(); dropCard.classList.add("dragover"); });
    dropCard.addEventListener("dragleave", () => dropCard.classList.remove("dragover"));
    dropCard.addEventListener("drop", (e) => {
      e.preventDefault();
      dropCard.classList.remove("dragover");
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f && f.path) setFolder(f.path);
    });
  }

  setupKeyboardShortcuts();
}

let started = false;
const start = () => { if (!started) { started = true; init(); } };
window.addEventListener("pywebviewready", start);
// browser preview: no pywebview → start in demo mode
window.addEventListener("load", () => setTimeout(() => { if (!window.pywebview) start(); }, 400));
