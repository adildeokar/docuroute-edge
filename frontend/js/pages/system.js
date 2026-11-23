/* Edge System page - service health, architecture, HTTP communication and a live API console. */
Pages.system = {
  title: "Edge System",
  subtitle: "Service health, architecture and HTTP communication",

  async show(el) {
    const [h, s] = await Promise.all([API.get("/api/health"), API.get("/api/stats")]);
    const up = h.uptime_s > 3600 ? `${Math.floor(h.uptime_s / 3600)}h ${Math.floor((h.uptime_s % 3600) / 60)}m` : `${Math.floor(h.uptime_s / 60)}m ${h.uptime_s % 60}s`;
    const node = (title, sub) => `<div class="node"><b>${title}</b><small>${sub}</small></div>`;
    const arr = `<div class="arr">${ICONS.arrow}</div>`;
    const endpoints = ["/api/health", "/api/stats", "/api/categories", "/api/documents?limit=3", "/api/departments", "/api/model"];

    el.innerHTML = `
      <div class="grid g-4">
        <div class="card kpi"><div class="kpi-label"><span class="kpi-icon">${ICONS.bolt}</span>Service status</div><div class="kpi-value" style="color:var(--good)">● Online</div><div class="kpi-sub">uptime ${up} · host ${esc(h.host)}</div></div>
        <div class="card kpi"><div class="kpi-label"><span class="kpi-icon">${ICONS.brain}</span>ML model</div><div class="kpi-value" style="font-size:19px">v${h.model_version} · ${esc(h.model_name)}</div><div class="kpi-sub">${h.model_loaded ? "loaded in memory" : "not loaded"}</div></div>
        <div class="card kpi"><div class="kpi-label"><span class="kpi-icon">${ICONS.scan}</span>OCR engine</div><div class="kpi-value" style="font-size:19px">${h.ocr_ready ? "Ready" : "Warming up…"}</div><div class="kpi-sub">${esc(h.ocr_engine)}</div></div>
        <div class="card kpi"><div class="kpi-label"><span class="kpi-icon">${ICONS.sparkle}</span>AI assistant (optional)</div><div class="kpi-value" style="font-size:19px">${h.ai_enabled ? "Enabled" : "Disabled"}</div><div class="kpi-sub">${h.ai_enabled ? esc(h.ai_model) + " · on-demand only" : "running fully offline"}</div></div>
      </div>

      <div class="card mt"><div class="card-head"><h3>Architecture</h3><span class="muted">${esc(h.platform)}</span></div>
        <div class="arch">
          ${node("Input devices", "Dashboard upload · scanner simulator · any HTTP client")}${arr}
          ${node("Flask edge service", "REST API on port 5000")}${arr}
          ${node("Text extraction", "RapidOCR (ONNX) · PDF text · DOCX/TXT")}${arr}
          ${node("ML classifier", "TF-IDF + " + esc(h.model_name))}${arr}
          ${node("Decision rules", "threshold · out-of-domain · duplicates")}${arr}
          ${node("Router + SQLite", "department folders · history DB")}
        </div>
        <div class="grid g-3 mt">
          <div class="alert alert-info">${ICONS.shield}<span><b>Privacy:</b> documents, OCR and predictions never leave the device. Only the optional AI button calls the cloud, with IDs masked.</span></div>
          <div class="alert alert-info">${ICONS.bolt}<span><b>Low latency:</b> ~${fmtMs(s.avg_classify_ms)} for the ML step and ~${fmtMs(s.avg_extraction_ms)} for OCR on a CPU. No upload to a server needed.</span></div>
          <div class="alert alert-info">${ICONS.check}<span><b>Works offline:</b> ${esc(h.inference)}. Chart library and fonts are bundled locally too.</span></div>
        </div>
      </div>

      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Live API console</h3><span class="muted">HTTP communication demo</span></div>
          <div class="row"><select id="apiSel" style="flex:1">${endpoints.map((e) => `<option>${e}</option>`).join("")}</select>
            <button class="btn btn-primary" id="apiBtn">Send GET</button></div>
          <div class="muted small mt" id="apiMeta">Pick an endpoint and press Send, the raw JSON response from the edge service is shown below.</div>
          <pre class="text mt" id="apiOut" style="max-height:340px">{ }</pre></div>
        <div class="card"><div class="card-head"><h3>Traffic by input source</h3><span class="muted">who is talking to the edge service</span></div>
          <div class="table-wrap"><table><thead><tr><th>Source</th><th>Documents</th></tr></thead><tbody>
            ${Object.entries(s.by_source).map(([k, v]) => `<tr><td><b>${esc(k)}</b></td><td>${v}</td></tr>`).join("") || '<tr><td colspan="2" class="muted">No traffic yet</td></tr>'}
          </tbody></table></div>
          <div class="section-title">Send documents from another device</div>
          <pre class="text"># Scanner / device simulator (separate program, talks HTTP)
python scanner_simulator.py --folder ../sample_documents/normal --interval 2

# Any HTTP client, e.g. curl
curl -F "file=@invoice.png" -F "source=curl" http://${esc(location.host || "localhost:5000")}/api/classify</pre></div>
      </div>`;

    el.querySelector("#apiBtn").onclick = async () => {
      const path = el.querySelector("#apiSel").value;
      const t0 = performance.now();
      try {
        const res = await fetch(API_BASE + path);
        const json = await res.json();
        el.querySelector("#apiMeta").innerHTML = `<b>GET ${esc(path)}</b> → HTTP ${res.status} · ${Math.round(performance.now() - t0)} ms · ${res.headers.get("content-type")}`;
        el.querySelector("#apiOut").textContent = JSON.stringify(json, null, 2).slice(0, 6000);
      } catch (e) { el.querySelector("#apiOut").textContent = e.message; }
    };
  },
};
