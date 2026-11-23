/* Classify page - upload new documents (live prediction), paste text, or use the demo sample gallery. */
Pages.classify = {
  title: "Classify Document",
  subtitle: "Upload a new document and watch it get classified and routed in real time",
  queue: [],          // [{name, status: pending|processing|done|error, doc, error}]
  selected: null,
  tab: "upload",
  rendered: false,

  async show(el) {
    if (!this.rendered) { this.render(el); this.rendered = true; }
    this.renderQueue();
  },

  render(el) {
    el.innerHTML = `
      <div class="grid g-2">
        <div class="card">
          <div class="tabs">
            <button data-tab="upload" class="active">${ICONS.download} Upload files</button>
            <button data-tab="text">${ICONS.file} Paste text</button>
            <button data-tab="samples">${ICONS.folder} Sample gallery</button>
          </div>

          <div data-panel="upload">
            <label class="dropzone" id="dropzone">
              <div class="dz-icon">${ICONS.download}</div>
              <h3>Drop documents here or click to browse</h3>
              <div class="muted">Images (PNG, JPG, TIFF, BMP, WEBP), PDF, DOCX or TXT · several files at once · max ${State.maxMb || 15} MB each</div>
              <input type="file" id="fileInput" multiple hidden accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp,.pdf,.txt,.docx" />
            </label>
            <div class="row mt muted small" style="flex-wrap:nowrap">${ICONS.shield} Files never leave this device: OCR and classification run on the local edge service.</div>
          </div>

          <div data-panel="text" class="hidden">
            <textarea id="textInput" placeholder="Paste the text of a document here (e.g. copied from an e-mail or a PDF)…"></textarea>
            <div class="row mt">
              <button class="btn btn-primary" id="textBtn">${ICONS.brain} Classify text</button>
              <span class="spacer"></span>
              <button class="btn btn-sm" data-example="invoice">Example: invoice</button>
              <button class="btn btn-sm" data-example="medical">Example: lab report</button>
              <button class="btn btn-sm" data-example="random">Example: random text</button>
            </div>
          </div>

          <div data-panel="samples" class="hidden">
            <div class="muted small" style="margin-bottom:10px">Demo documents shipped with the project (<span class="mono">sample_documents/</span>). Click one to send it through the full pipeline. The <b style="color:var(--bad)">abnormal</b> group tests edge cases.</div>
            <div class="samples" id="samples"><div class="spinner"></div></div>
          </div>
        </div>

        <div class="card">
          <div class="card-head"><h3>Processing queue</h3>
            <button class="btn btn-sm" id="clearQueue">Clear</button></div>
          <div class="queue" id="queue" style="max-height:440px;margin:0"></div>
        </div>
      </div>
      <div class="mt" id="result"></div>`;

    // tabs
    el.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => {
      el.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("active", x === b));
      el.querySelectorAll("[data-panel]").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== b.dataset.tab));
      if (b.dataset.tab === "samples") this.loadSamples();
    }));

    // drag & drop upload
    const dz = el.querySelector("#dropzone"), input = el.querySelector("#fileInput");
    input.onchange = () => { this.addFiles([...input.files]); input.value = ""; };
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("drag"); }));
    dz.addEventListener("drop", (e) => this.addFiles([...e.dataTransfer.files]));

    // text
    const EXAMPLES = {
      invoice: "TAX INVOICE\nNova Supplies Co.\nInvoice No: INV-20931\nInvoice Date: 12/03/2026\nBill To: Apex Technologies Pvt Ltd\nDescription | Qty | Unit Price | Amount\nPrinter Toner | 4 | 2,500.00 | 10,000.00\nSubtotal: 10,000.00\nGST 18%: 1,800.00\nTotal Amount Due: Rs. 11,800.00\nPayment Terms: Net 30",
      medical: "LifeLine Pathology Lab\nPatient Name: Riya Sharma   Age/Sex: 34 Y / F\nReferred By: Dr. Mehta\nTest Name | Result | Unit | Reference Range\nHemoglobin | 12.1 | g/dL | 12.0 - 15.0\nBlood Sugar Fasting | 96 | mg/dL | 70 - 110\nTSH | 2.3 | uIU/mL | 0.4 - 4.0\n*** End of Report ***",
      random: "The match was postponed due to heavy rain. Fans waited for hours in the stadium while the ground staff tried to cover the pitch. The captain said the team will practise indoors tomorrow.",
    };
    el.querySelectorAll("[data-example]").forEach((b) => (b.onclick = () => (el.querySelector("#textInput").value = EXAMPLES[b.dataset.example])));
    el.querySelector("#textBtn").onclick = () => {
      const text = el.querySelector("#textInput").value.trim();
      if (!text) return toast("Paste some text first", "err");
      this.run("Pasted text", () => API.classifyText(text));
    };
    el.querySelector("#clearQueue").onclick = () => { this.queue = []; this.selected = null; this.renderQueue(); el.querySelector("#result").innerHTML = ""; };
  },

  async loadSamples() {
    const box = document.getElementById("samples");
    if (box.dataset.loaded) return;
    try {
      const samples = await API.get("/api/samples");
      const img = ["png", "jpg", "jpeg"];
      const tile = (s) => `<div class="sample ${s.group === "abnormal" ? "abn" : ""}" data-path="${esc(s.path)}" title="${esc(s.name)}">
        <div class="thumb">${img.includes(s.ext) && !s.name.includes("corrupted") ? `<img loading="lazy" src="${API.sampleUrl(s.path)}">` : extTag(s.ext)}</div>
        <div class="meta">${esc(s.name)}</div></div>`;
      box.innerHTML = `<div class="group-title">Normal documents</div>${samples.filter((s) => s.group === "normal").map(tile).join("")}
        <div class="group-title">Abnormal / edge cases</div>${samples.filter((s) => s.group === "abnormal").map(tile).join("")}`;
      box.dataset.loaded = 1;
      box.querySelectorAll(".sample").forEach((t) => (t.onclick = () =>
        this.run(t.title, () => API.post("/api/samples/classify", { path: t.dataset.path }))));
    } catch (e) { box.innerHTML = emptyState(e.message); }
  },

  addFiles(files) {
    files.forEach((f) => this.run(f.name, () => API.classifyFile(f)));
  },

  /** Add a job to the queue; jobs run one after another (like a scanner feeding the edge device). */
  run(name, fn) {
    const item = { name, status: "pending", fn };
    this.queue.unshift(item);
    this.renderQueue();
    this.chain = (this.chain || Promise.resolve()).then(async () => {
      item.status = "processing"; this.renderQueue();
      try {
        item.doc = await fn();
        item.status = "done";
        this.select(item);
      } catch (e) {
        item.status = "error"; item.error = e.message;
        toast(`${name}: ${e.message}`, "err");
        this.select(item);
      }
      this.renderQueue();
      refreshBadges();
    });
  },

  renderQueue() {
    const q = document.getElementById("queue");
    if (!q) return;
    if (!this.queue.length) { q.innerHTML = emptyState("Nothing processed in this session yet.<br>Upload a file, paste text or pick a sample."); return; }
    q.innerHTML = this.queue.map((it, i) => {
      let right = '<span class="muted small">waiting…</span>';
      if (it.status === "processing") right = '<span class="spinner"></span><span class="muted small">OCR + classifying…</span>';
      if (it.status === "error") right = `<span class="status st-needs_review" style="background:var(--bad-soft);color:var(--bad)">${ICONS.x}Rejected</span>`;
      if (it.status === "done") right = `${catBadge(it.doc.final_category)}<b class="small">${pct(it.doc.confidence, 0)}</b>`;
      return `<div class="q-item ${it === this.selected ? "sel" : ""}" data-i="${i}">${extTag(it.name.includes(".") ? it.name.split(".").pop().slice(0, 4) : "txt")}<span class="name">${esc(it.name)}</span>${right}</div>`;
    }).join("");
    q.querySelectorAll(".q-item").forEach((n) => (n.onclick = () => { const it = this.queue[n.dataset.i]; if (it.status === "done" || it.status === "error") this.select(it); }));
  },

  select(item) {
    this.selected = item;
    const box = document.getElementById("result");
    if (item.status === "error") {
      box.innerHTML = `<div class="card"><div class="alert alert-danger">${ICONS.x}<span><b>${esc(item.name)} was rejected by the edge service.</b><br>${esc(item.error)}</span></div>
        <p class="muted small" style="margin-bottom:0">Abnormal input handled safely: nothing was routed and the service keeps running.</p></div>`;
    } else {
      box.innerHTML = docDetailHtml(item.doc);
      bindDocActions(box, (doc) => { if (doc) { item.doc = doc; this.select(item); } else { this.queue.splice(this.queue.indexOf(item), 1); box.innerHTML = ""; } this.renderQueue(); });
    }
    this.renderQueue();
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  },
};
