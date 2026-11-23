/* Departments page - the routing table and what each department folder has received. */
Pages.departments = {
  title: "Departments",
  subtitle: "Routing table: each category is delivered to a department folder",

  async show(el) {
    const depts = await API.get("/api/departments");
    el.innerHTML = `
      <div class="card" style="margin-bottom:18px">
        <div class="card-head"><h3>Routing table</h3><span class="muted">configured in backend/config.py</span></div>
        <div class="table-wrap"><table><thead><tr><th>Predicted category</th><th></th><th>Department</th><th>Folder on edge device</th><th>Purpose</th></tr></thead><tbody>
        ${depts.map((d) => `<tr><td>${catBadge(d.key)}</td><td class="muted">${ICONS.arrow}</td><td><b>${esc(d.department)}</b></td>
          <td class="mono small">${esc(d.path)}/</td><td class="muted small">${esc(d.description)}</td></tr>`).join("")}
        </tbody></table></div>
      </div>
      <div class="grid g-3">
        ${depts.map((d) => `<div class="card dept" style="--c:${catColor(d.key)}">
          <div class="row"><div style="flex:1;min-width:0"><div class="muted small">${esc(catInfo(d.key).label)}</div><h3 style="font-size:15px">${esc(d.department)}</h3></div>
            <div style="text-align:right"><div class="dept-count">${d.files || 0}</div><div class="muted small">files · ${d.size_kb || 0} KB</div></div></div>
          <ul>${d.recent.length ? d.recent.map((r) => `<li class="clickable" data-id="${r.id}" style="cursor:pointer"><span>#${r.id} ${esc(r.filename)}</span><span class="muted">${pct(r.confidence, 0)}</span></li>`).join("") : '<li><span class="muted">No documents yet</span></li>'}</ul>
          <button class="btn btn-sm mt" data-dept="${esc(d.department)}">View all in history →</button>
        </div>`).join("")}
      </div>`;
    el.querySelectorAll("[data-id]").forEach((r) => (r.onclick = () => showDocument(r.dataset.id, () => this.show(el))));
    el.querySelectorAll("[data-dept]").forEach((b) => (b.onclick = () => {
      Pages.history.filters = { search: "", category: "", status: "", department: b.dataset.dept };
      location.hash = "history";
    }));
  },
};
