/* ui.js - shared helpers and reusable UI components used by every page. */
const State = { cats: {}, unknown: null, threshold: 0.7, health: null, charts: {} };

const ICONS = {
  file: '<svg viewBox="0 0 24 24"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/></svg>',
  scan: '<svg viewBox="0 0 24 24"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/></svg>',
  brain: '<svg viewBox="0 0 24 24"><path d="M12 2a4 4 0 0 1 4 4v1h1a3 3 0 0 1 0 6h-1v1a4 4 0 0 1-8 0v-1H7a3 3 0 0 1 0-6h1V6a4 4 0 0 1 4-4z"/></svg>',
  folder: '<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
  x: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 5l7 7-7 7"/></svg>',
  sparkle: '<svg viewBox="0 0 24 24"><path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/></svg>',
  download: '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  gauge: '<svg viewBox="0 0 24 24"><path d="M12 14l4-4"/><path d="M3.3 19a10 10 0 1 1 17.4 0"/></svg>',
  inbox: '<svg viewBox="0 0 24 24"><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z"/></svg>',
  shield: '<svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
  bolt: '<svg viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9z"/></svg>',
};

/* ---------- formatting ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (v, d = 1) => (v == null ? "—" : (v * 100).toFixed(d) + "%");
const fmtMs = (ms) => (ms == null ? "—" : ms >= 1000 ? (ms / 1000).toFixed(2) + " s" : Math.round(ms) + " ms");
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
const fmtSize = (b) => (b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB");
const isDark = () => document.documentElement.dataset.theme === "dark" ||
  (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);

function catInfo(key) { return State.cats[key] || State.unknown || { label: key, color: "#64748b", department: "—" }; }
function catColor(key) { const c = catInfo(key); return isDark() ? c.color_dark || c.color : c.color; }
function catBadge(key) { return `<span class="badge"><span class="sw" style="background:${catColor(key)}"></span>${esc(catInfo(key).label)}</span>`; }

const STATUS = {
  auto_routed: ["Auto-routed", ICONS.check], needs_review: ["Needs review", ICONS.alert],
  reviewed: ["Human confirmed", ICONS.shield], corrected: ["Human corrected", ICONS.shield],
};
function statusBadge(s) { const [label, icon] = STATUS[s] || [s, ""]; return `<span class="status st-${s}">${icon}${label}</span>`; }

function confBar(conf) {
  const color = conf >= State.threshold ? "var(--good)" : conf >= 0.5 ? "#f59e0b" : "#ef4444";
  return `<div class="conf-bar"><div class="track"><div class="fill" style="width:${(conf || 0) * 100}%;background:${color}"></div></div><b>${pct(conf, 0)}</b></div>`;
}
const extTag = (ext) => `<span class="ext">${esc(ext || "?")}</span>`;
const emptyState = (msg, icon = ICONS.inbox) => `<div class="empty">${icon}<div>${msg}</div></div>`;

/* ---------- toast / modal ---------- */
function toast(msg, type = "") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.getElementById("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4200);
}
function openModal(title, html) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalBody").innerHTML = html;
  document.getElementById("modal").classList.add("open");
}
function closeModal() { document.getElementById("modal").classList.remove("open"); }

/* ---------- charts (Chart.js) ---------- */
function makeChart(id, config) {
  if (State.charts[id]) State.charts[id].destroy();
  const el = document.getElementById(id);
  if (!el) return;
  const css = getComputedStyle(document.documentElement);
  Chart.defaults.color = css.getPropertyValue("--text-2").trim();
  Chart.defaults.borderColor = css.getPropertyValue("--grid").trim();
  Chart.defaults.font.family = "Segoe UI, Inter, system-ui, sans-serif";
  config.options = Object.assign({ responsive: true, maintainAspectRatio: false, animation: { duration: 500 } }, config.options || {});
  State.charts[id] = new Chart(el, config);
}

/* ---------- confidence ring ---------- */
function ring(conf, color) {
  const r = 48, c = 2 * Math.PI * r, off = c * (1 - (conf || 0));
  return `<div class="ring"><svg viewBox="0 0 110 110"><circle class="bg" cx="55" cy="55" r="${r}" stroke-width="10" fill="none"/>
    <circle class="val" cx="55" cy="55" r="${r}" stroke-width="10" fill="none" stroke="${color}" stroke-linecap="round"
    stroke-dasharray="${c}" stroke-dashoffset="${off}"/></svg><div class="lbl"><div><b>${pct(conf, 0)}</b><span>confidence</span></div></div></div>`;
}

/* ---------- document detail (used by Classify page, History modal, Review page) ---------- */
function previewHtml(doc) {
  const url = API.fileUrl(doc.id);
  if (["png", "jpg", "jpeg", "bmp", "webp"].includes(doc.file_ext)) return `<div class="preview"><img src="${url}" alt="document preview"/></div>`;
  if (doc.file_ext === "pdf") return `<div class="preview"><iframe src="${url}"></iframe></div>`;
  return `<div class="preview" style="padding:30px;text-align:center">${extTag(doc.file_ext)}<div class="muted small" style="margin-top:8px">No visual preview for this file type</div></div>`;
}

function aiHtml(ai) {
  if (!ai) return "";
  const fields = Object.entries(ai.key_fields || {}).map(([k, v]) => `<div>${esc(k)}</div><div>${esc(v)}</div>`).join("");
  return `<div class="ai-box">
    <div class="row"><b>${ICONS.sparkle} AI summary</b><span class="spacer"></span>
      <span class="badge">${ai.agrees_with_model ? "Agrees with local model" : "Suggests: " + esc(ai.suggested_category)}</span>
      <span class="badge">Priority: ${esc(ai.priority)}</span></div>
    <p style="margin:10px 0">${esc(ai.summary)}</p>
    <div class="muted small" style="margin-bottom:8px">${esc(ai.reason || "")}</div>
    ${fields ? `<div class="kv">${fields}</div>` : ""}
    ${(ai.action_items || []).length ? `<div style="margin-top:10px"><b>Next actions</b><ul>${ai.action_items.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}
    <div class="muted small" style="margin-top:8px">${esc(ai.model)} · ${ai.tokens_used || "?"} tokens · personal numbers were masked before sending</div>
  </div>`;
}

function docDetailHtml(doc) {
  const info = catInfo(doc.final_category);
  const color = catColor(doc.final_category);
  const review = doc.status === "needs_review";
  const suggestion = doc.predicted_category !== "unknown" ? catInfo(doc.predicted_category).label : null;
  const probs = (doc.probabilities || []).map((p) => `
    <div class="prob"><span>${catBadge(p.category)}</span>
      <div class="track"><div class="fill" style="width:${p.probability * 100}%;background:${catColor(p.category)}"></div></div>
      <span class="pct">${pct(p.probability)}</span></div>`).join("");
  const terms = (doc.top_terms || []).map((t) => `<span class="term">${esc(t.term)}<small>+${t.weight.toFixed(2)}</small></span>`).join("");
  const fields = Object.entries(doc.key_fields || {}).map(([k, v]) => `<div>${esc(k.replace(/_/g, " "))}</div><div>${esc(v)}</div>`).join("");
  const alerts = (doc.alerts || []).map((a) => `<div class="alert alert-${a.level}">${a.level === "info" ? ICONS.info : a.level === "warning" ? ICONS.alert : ICONS.x}<span>${esc(a.message)}</span></div>`).join("");
  const options = Object.entries(State.cats).map(([k, c]) => `<option value="${k}" ${k === (doc.final_category !== "unknown" ? doc.final_category : doc.predicted_category) ? "selected" : ""}>${esc(c.label)}</option>`).join("");
  const aiDisabled = !(State.health && State.health.ai_enabled);

  return `<div class="grid g-main">
    <div>
      <div class="card">
        <div class="steps">
          <div class="step done"><div class="c">${ICONS.file}</div><div class="t">Received</div><div class="s">${esc(doc.source)}</div></div>
          <div class="step done"><div class="c">${ICONS.scan}</div><div class="t">Text extracted</div><div class="s">${fmtMs(doc.extraction_ms)}</div></div>
          <div class="step done"><div class="c">${ICONS.brain}</div><div class="t">Classified</div><div class="s">${doc.predicted_category === "unknown" ? "skipped" : fmtMs(doc.classify_ms)}</div></div>
          <div class="step ${review ? "warn" : "done"}"><div class="c">${review ? ICONS.alert : ICONS.folder}</div><div class="t">${review ? "Manual review" : "Routed"}</div><div class="s">total ${fmtMs(doc.total_ms)}</div></div>
        </div>
        <div class="result-head">
          ${ring(doc.confidence, review ? "#f59e0b" : color)}
          <div style="flex:1;min-width:200px">
            <div class="muted small">Document #${doc.id} · ${esc(doc.filename)}</div>
            <div class="cat-title" style="color:${color}">${esc(info.label)}</div>
            <div class="row" style="margin-top:6px">${statusBadge(doc.status)}
              ${review && suggestion ? `<span class="badge">Model suggestion: ${esc(suggestion)}</span>` : ""}
              <span class="badge">Model v${doc.model_version}</span></div>
          </div>
        </div>
        <div class="route-box">
          <div class="ico" style="background:${color}">${ICONS.folder}</div>
          <div style="flex:1;min-width:0"><div class="muted small">Routed to department</div><b>${esc(doc.department)}</b>
            <div class="mono small muted" style="overflow-wrap:anywhere">data/routed/${esc(doc.routed_path)}</div></div>
        </div>
        ${alerts ? `<div class="alerts">${alerts}</div>` : ""}

        ${probs ? `<div class="section-title">${ICONS.gauge} Probability for every category</div>${probs}` : ""}
        ${terms ? `<div class="section-title">${ICONS.brain} Why this prediction? (words that influenced the model)</div><div class="terms">${terms}</div>` : ""}
        ${fields ? `<div class="section-title">${ICONS.scan} Key fields (extracted locally)</div><div class="kv">${fields}</div>` : ""}

        <div class="section-title">${ICONS.shield} Human review</div>
        <div class="row">
          <select id="reviewSelect-${doc.id}">${options}</select>
          <button class="btn ${review ? "btn-primary" : ""}" data-act="review" data-id="${doc.id}">${ICONS.check} Confirm / Reassign</button>
          <span class="muted small">Moves the file to the chosen department and adds it to retraining data.</span>
        </div>

        <div class="section-title">${ICONS.sparkle} AI insights <span class="muted small" style="text-transform:none;letter-spacing:0">(optional · ${esc(State.health?.ai_model || "OpenAI")})</span></div>
        <div id="ai-${doc.id}">${doc.ai_insights ? aiHtml(doc.ai_insights) :
          `<button class="btn" data-act="ai" data-id="${doc.id}" ${aiDisabled ? "disabled" : ""}>${ICONS.sparkle} Generate AI summary &amp; key fields</button>
           <span class="muted small" style="margin-left:8px">${aiDisabled ? "Disabled - add OPENAI_API_KEY to backend/.env" : "Cloud call, only on request. IDs & e-mails are masked first."}</span>`}</div>
      </div>
    </div>

    <div>
      <div class="card">
        <div class="card-head"><h3>Original document</h3>
          <div class="row"><a class="btn btn-sm" href="${API.fileUrl(doc.id, true)}">${ICONS.download} Download</a>
          <button class="btn btn-sm btn-danger" data-act="delete" data-id="${doc.id}">${ICONS.trash}</button></div></div>
        ${previewHtml(doc)}
        <div class="section-title">Extracted text (${(doc.text || "").length} chars)</div>
        <pre class="text">${esc(doc.text || "(no text detected)")}</pre>
        <div class="section-title">Processing details</div>
        <div class="kv">
          <div>Extraction</div><div>${esc(doc.extraction_method)}</div>
          <div>OCR confidence</div><div>${doc.ocr_confidence == null ? "n/a (digital text)" : pct(doc.ocr_confidence)}</div>
          <div>Familiar words</div><div>${pct(doc.known_word_ratio, 0)}</div>
          <div>File</div><div>${esc(doc.file_ext).toUpperCase()} · ${fmtSize(doc.file_size)} · ${doc.pages} page(s)</div>
          <div>Timing</div><div>OCR ${fmtMs(doc.extraction_ms)} · ML ${fmtMs(doc.classify_ms)} · total ${fmtMs(doc.total_ms)}</div>
          <div>SHA-256</div><div class="mono small">${esc((doc.file_hash || "").slice(0, 24))}…</div>
          <div>Processed</div><div>${new Date(doc.created_at).toLocaleString()}</div>
        </div>
      </div>
    </div>
  </div>`;
}

/** Wire up buttons inside a rendered document detail. onChange(updatedDoc|null) is called after changes. */
function bindDocActions(container, onChange) {
  container.querySelectorAll("[data-act]").forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.dataset.id;
      try {
        if (btn.dataset.act === "review") {
          const category = container.querySelector(`#reviewSelect-${id}`).value;
          const doc = await API.post(`/api/documents/${id}/review`, { category });
          toast(`Document #${id} routed to ${doc.department}`, "ok");
          onChange && onChange(doc);
        } else if (btn.dataset.act === "ai") {
          btn.disabled = true;
          btn.innerHTML = `<span class="spinner"></span> Asking ${esc(State.health?.ai_model || "AI")}…`;
          const ai = await API.post(`/api/documents/${id}/ai`);
          container.querySelector(`#ai-${id}`).innerHTML = aiHtml(ai);
        } else if (btn.dataset.act === "delete") {
          if (!confirm(`Delete document #${id} and its routed file?`)) return;
          await API.del(`/api/documents/${id}`);
          toast(`Document #${id} deleted`, "ok");
          onChange && onChange(null);
        }
        refreshBadges();
      } catch (e) {
        toast(e.message, "err");
        if (btn.dataset.act === "ai") { btn.disabled = false; btn.innerHTML = `${ICONS.sparkle} Retry AI summary`; }
      }
    };
  });
}

async function showDocument(id, onChange) {
  try {
    const doc = await API.get(`/api/documents/${id}`);
    openModal(`Document #${doc.id} - ${doc.filename}`, docDetailHtml(doc));
    bindDocActions(document.getElementById("modalBody"), (d) => {
      if (d) showDocument(d.id, onChange); else closeModal();
      onChange && onChange(d);
    });
  } catch (e) { toast(e.message, "err"); }
}

async function refreshBadges() {
  try {
    const s = await API.get("/api/stats");
    const b = document.getElementById("reviewBadge");
    b.textContent = s.needs_review;
    b.classList.toggle("zero", s.needs_review === 0);
  } catch (_) { /* service offline - handled by health check */ }
}
