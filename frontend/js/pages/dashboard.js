/* Dashboard page - live overview of everything the edge service has processed. */
const Pages = {};

Pages.dashboard = {
  title: "Dashboard",
  subtitle: "Live overview of document classification and routing",
  lastSignature: "",

  async show(el, force = true) {
    let s;
    try { s = await API.get("/api/stats"); } catch (e) { el.innerHTML = emptyState("Edge service is not reachable. Start it with <b>python app.py</b>"); return; }
    const sig = JSON.stringify([s.total, s.by_status, s.recent.map((r) => r.id + r.status)]);
    if (!force && sig === this.lastSignature) return;       // nothing new -> don't redraw (no flicker)
    this.lastSignature = sig;

    const autoRate = s.total ? (s.by_status.auto_routed || 0) / s.total : 0;
    const kpi = (label, value, sub, icon) => `<div class="card kpi"><div class="kpi-label"><span class="kpi-icon">${icon}</span>${label}</div>
      <div class="kpi-value">${value}</div><div class="kpi-sub">${sub}</div></div>`;

    el.innerHTML = `
      <div class="hero">
        <div>
          <h2>Edge Document Intelligence</h2>
          <p>Upload scans, photos, PDFs or text. The document is read by on-device OCR, classified by a local ML model and routed to the right department in seconds, without any cloud dependency.</p>
          <div class="flow"><span>Upload</span><i>→</i><span>OCR</span><i>→</i><span>TF-IDF + ML</span><i>→</i><span>Decision rules</span><i>→</i><span>Department folder</span></div>
        </div>
        <div class="actions">
          <a class="btn" href="#classify">${ICONS.scan} Classify a document</a>
          <a class="btn ghost" href="#review">${ICONS.shield} Review queue (${s.needs_review})</a>
        </div>
      </div>

      <div class="grid g-6 mt">
        ${kpi("Documents processed", s.total, `${Object.keys(s.by_source).length} input source(s)`, ICONS.file)}
        ${kpi("Auto-routed", pct(autoRate, 0), `${s.by_status.auto_routed || 0} without human help`, ICONS.bolt)}
        ${kpi("Needs review", s.needs_review, "low confidence / unreadable", ICONS.alert)}
        ${kpi("Avg confidence", pct(s.avg_confidence, 1), "on classified documents", ICONS.gauge)}
        ${kpi("Avg processing", fmtMs(s.avg_processing_ms), `OCR ${fmtMs(s.avg_extraction_ms)} · ML ${fmtMs(s.avg_classify_ms)}`, ICONS.clock)}
        ${kpi("Live accuracy", s.live_accuracy == null ? "—" : pct(s.live_accuracy, 0), `${s.human_verified} human-verified docs`, ICONS.shield)}
      </div>

      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Documents by category</h3><span class="live"><span class="dot on"></span>LIVE</span></div>
          <div class="chart-box"><canvas id="chCategory"></canvas></div></div>
        <div class="card"><div class="card-head"><h3>Daily volume</h3><span class="muted">last 14 days</span></div>
          <div class="chart-box"><canvas id="chDaily"></canvas></div></div>
      </div>
      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Prediction confidence</h3><span class="muted">threshold ${pct(State.threshold, 0)}</span></div>
          <div class="chart-box sm"><canvas id="chConf"></canvas></div></div>
        <div class="card"><div class="card-head"><h3>Routing outcome</h3><span class="muted">auto vs human</span></div>
          <div class="chart-box sm"><canvas id="chStatus"></canvas></div></div>
      </div>

      <div class="grid g-main mt">
        <div class="card"><div class="card-head"><h3>Recent documents</h3><a href="#history" class="small">View all →</a></div>
          <div class="table-wrap">${s.recent.length ? `<table><thead><tr><th>#</th><th>File</th><th>Category</th><th>Confidence</th><th>Status</th><th>Time</th></tr></thead><tbody>
            ${s.recent.map((d) => `<tr class="clickable" data-id="${d.id}"><td>${d.id}</td><td><div class="file-cell"><span>${esc(d.filename)}</span></div></td>
              <td>${catBadge(d.final_category)}</td><td>${confBar(d.confidence)}</td><td>${statusBadge(d.status)}</td>
              <td class="muted small">${fmtDate(d.created_at)}</td></tr>`).join("")}
            </tbody></table>` : emptyState('No documents yet - go to <a href="#classify">Classify Document</a> and upload one.')}</div></div>
        <div class="card"><div class="card-head"><h3>Alerts</h3><span class="muted">${s.alerts.length} recent</span></div>
          <div class="alerts" style="margin:0;max-height:420px;overflow-y:auto">${s.alerts.length ? s.alerts.map((a) => `
            <div class="alert alert-${a.level} clickable" data-id="${a.doc_id}" style="cursor:pointer">${a.level === "info" ? ICONS.info : a.level === "warning" ? ICONS.alert : ICONS.x}
            <span><b>#${a.doc_id} ${esc(a.filename)}</b><br>${esc(a.message)}</span></div>`).join("") : emptyState("No alerts. All clear.", ICONS.check)}</div></div>
      </div>`;

    el.querySelectorAll("[data-id]").forEach((r) => (r.onclick = () => showDocument(r.dataset.id, () => this.show(el))));
    this.drawCharts(s);
  },

  drawCharts(s) {
    const keys = [...Object.keys(State.cats), "unknown"];
    makeChart("chCategory", {
      type: "bar",
      data: { labels: keys.map((k) => catInfo(k).label),
              datasets: [{ data: keys.map((k) => s.by_category[k] || 0), backgroundColor: keys.map(catColor), borderRadius: 4, barThickness: 16 }] },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } } },
    });
    makeChart("chDaily", {
      type: "bar",
      data: { labels: s.daily.map((d) => d.date.slice(5)), datasets: [{ label: "Documents", data: s.daily.map((d) => d.count), backgroundColor: "#4f46e5", borderRadius: 4, maxBarThickness: 26 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } } },
    });
    const b = s.confidence_buckets;
    makeChart("chConf", {
      type: "bar",
      data: { labels: Object.keys(b), datasets: [{ label: "Documents", data: Object.values(b), backgroundColor: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"], borderRadius: 4, maxBarThickness: 48 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } } },
    });
    const st = ["auto_routed", "needs_review", "reviewed", "corrected"];
    makeChart("chStatus", {
      type: "doughnut",
      data: { labels: st.map((x) => STATUS[x][0]), datasets: [{ data: st.map((x) => s.by_status[x] || 0),
        backgroundColor: ["#22a559", "#f59e0b", "#3b82f6", "#7c3aed"], borderColor: getComputedStyle(document.documentElement).getPropertyValue("--surface"), borderWidth: 2 }] },
      options: { cutout: "64%", plugins: { legend: { position: "right", labels: { usePointStyle: true, boxWidth: 8 } } } },
    });
  },
};
