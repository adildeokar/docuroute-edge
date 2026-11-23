/* main.js - start-up, page navigation (hash router), health polling and theme switch. */

async function loadHealth() {
  const dot = document.getElementById("sideDot"), txt = document.getElementById("sideStatus");
  try {
    const h = await API.get("/api/health");
    State.health = h;
    dot.className = "dot on";
    txt.textContent = "Edge service online";
    document.getElementById("modelPill").innerHTML = `${ICONS.brain} Model v${h.model_version}`;
    document.getElementById("aiPill").innerHTML = `${ICONS.sparkle} AI ${h.ai_enabled ? "on-demand" : "off"}`;
  } catch (_) {
    State.health = null;
    dot.className = "dot off";
    txt.textContent = "Edge service offline";
  }
}

async function navigate() {
  // hash format: "#page" or "#page/<documentId>" (deep link that opens a document)
  const [name, docId] = (location.hash || "#dashboard").slice(1).split("/");
  const page = Pages[name] ? name : "dashboard";
  if (docId) setTimeout(() => showDocument(docId), 0);
  document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === page));
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === "page-" + page));
  document.getElementById("pageTitle").textContent = Pages[page].title;
  document.getElementById("pageSubtitle").textContent = Pages[page].subtitle;
  document.getElementById("sidebar").classList.remove("open");
  try {
    await Pages[page].show(document.getElementById("page-" + page));
  } catch (e) {
    document.getElementById("page-" + page).innerHTML = emptyState(`Could not load this page: ${esc(e.message)}`);
  }
}

function setupTheme() {
  const saved = (() => { try { return localStorage.getItem("theme"); } catch (_) { return null; } })();
  if (saved) document.documentElement.dataset.theme = saved;
  document.getElementById("themeBtn").onclick = () => {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (_) { /* storage blocked - theme just won't persist */ }
    navigate();                                   // redraw charts with the new colours
  };
}

async function init() {
  setupTheme();
  document.getElementById("menuBtn").onclick = () => document.getElementById("sidebar").classList.toggle("open");
  document.getElementById("modalClose").onclick = closeModal;
  document.getElementById("modal").onclick = (e) => { if (e.target.id === "modal") closeModal(); };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  await loadHealth();
  try {
    const c = await API.get("/api/categories");
    c.categories.forEach((x) => (State.cats[x.key] = x));
    State.unknown = c.unknown;
    State.threshold = c.confidence_threshold;
    State.maxMb = c.max_upload_mb;
  } catch (_) { /* offline: pages will show an error state */ }

  window.addEventListener("hashchange", navigate);
  await navigate();
  refreshBadges();

  // Live updates: documents sent by the scanner simulator appear automatically
  setInterval(async () => {
    await loadHealth();
    refreshBadges();
    const current = (location.hash || "#dashboard").slice(1).split("/")[0];
    if (current === "dashboard" && !document.getElementById("modal").classList.contains("open")) {
      Pages.dashboard.show(document.getElementById("page-dashboard"), false);
    }
  }, 5000);
}

init();
