/* History page - classification records with filters, search and CSV export. */
Pages.history = {
  title: "Classification History",
  subtitle: "Every prediction with its confidence, department and status",
  filters: { search: "", category: "", status: "", department: "" },
  rendered: false,

  async show(el) {
    if (!this.rendered) {
      const catOpts = [...Object.keys(State.cats), "unknown"].map((k) => `<option value="${k}">${esc(catInfo(k).label)}</option>`).join("");
      el.innerHTML = `
        <div class="card">
          <div class="row" style="margin-bottom:14px">
            <input id="hSearch" placeholder="Search file name, text or department…" style="flex:1;min-width:220px" />
            <select id="hCategory"><option value="">All categories</option>${catOpts}</select>
            <select id="hStatus"><option value="">All statuses</option>${Object.entries(STATUS).map(([k, v]) => `<option value="${k}">${v[0]}</option>`).join("")}</select>
            <button class="btn btn-sm" id="hClear">Reset</button>
            <a class="btn btn-sm" href="${API_BASE}/api/export.csv">${ICONS.download} Export CSV</a>
          </div>
          <div id="hDept" class="hidden" style="margin-bottom:12px"></div>
          <div class="table-wrap" id="hTable"></div>
        </div>`;
      let timer;
      el.querySelector("#hSearch").oninput = (e) => { clearTimeout(timer); timer = setTimeout(() => { this.filters.search = e.target.value; this.load(); }, 300); };
      el.querySelector("#hCategory").onchange = (e) => { this.filters.category = e.target.value; this.load(); };
      el.querySelector("#hStatus").onchange = (e) => { this.filters.status = e.target.value; this.load(); };
      el.querySelector("#hClear").onclick = () => {
        this.filters = { search: "", category: "", status: "", department: "" };
        ["hSearch", "hCategory", "hStatus"].forEach((id) => (el.querySelector("#" + id).value = ""));
        this.load();
      };
      this.rendered = true;
    }
    // keep the filter inputs in sync (filters can also be set from the Departments page)
    el.querySelector("#hSearch").value = this.filters.search;
    el.querySelector("#hCategory").value = this.filters.category;
    el.querySelector("#hStatus").value = this.filters.status;
    this.load();
  },

  async load() {
    const box = document.getElementById("hTable");
    const dept = document.getElementById("hDept");
    dept.classList.toggle("hidden", !this.filters.department);
    dept.innerHTML = `<span class="badge">${ICONS.folder} Department: ${esc(this.filters.department)}</span>`;
    const qs = new URLSearchParams(this.filters).toString();
    const docs = await API.get(`/api/documents?${qs}`);
    box.innerHTML = docs.length ? `<table><thead><tr><th>#</th><th>File</th><th>Predicted</th><th>Confidence</th><th>Final category</th><th>Department</th><th>Status</th><th>Source</th><th>Time</th><th>Processed</th></tr></thead><tbody>
      ${docs.map((d) => `<tr class="clickable" data-id="${d.id}">
        <td class="muted">${d.id}</td>
        <td><div class="file-cell">${extTag(d.file_ext)}<span title="${esc(d.filename)}">${esc(d.filename)}</span></div></td>
        <td>${d.predicted_category === "unknown" ? '<span class="muted small">—</span>' : esc(catInfo(d.predicted_category).label)}</td>
        <td>${confBar(d.confidence)}</td>
        <td>${catBadge(d.final_category)}</td>
        <td class="small">${esc(d.department)}</td>
        <td>${statusBadge(d.status)}</td>
        <td class="muted small">${esc(d.source)}</td>
        <td class="muted small">${fmtMs(d.total_ms)}</td>
        <td class="muted small">${fmtDate(d.created_at)}</td></tr>`).join("")}</tbody></table>
      <div class="muted small" style="margin-top:10px">${docs.length} record(s)</div>` : emptyState("No documents match these filters.");
    box.querySelectorAll("tr[data-id]").forEach((r) => (r.onclick = () => showDocument(r.dataset.id, () => this.load())));
  },
};
