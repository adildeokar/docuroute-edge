/* Review Queue - human-in-the-loop for low-confidence / unreadable documents. */
Pages.review = {
  title: "Review Queue",
  subtitle: "Documents the model was not sure about - confirm or reassign them",

  async show(el) {
    const docs = await API.get("/api/documents?status=needs_review&limit=100");
    const options = (sel) => Object.entries(State.cats).map(([k, c]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${esc(c.label)}</option>`).join("");
    const isImg = (d) => ["png", "jpg", "jpeg", "bmp", "webp"].includes(d.file_ext);

    el.innerHTML = `
      <div class="card" style="margin-bottom:18px"><div class="row">
        <div class="kpi-icon">${ICONS.shield}</div>
        <div style="flex:1;min-width:240px"><b>${docs.length} document(s) waiting for a human decision</b>
          <div class="muted small">A document lands here when confidence &lt; ${pct(State.threshold, 0)}, the text is unreadable, or the content does not match any known type.
          Every decision moves the file to the right folder and becomes new training data (see <a href="#model">Model → Retrain</a>).</div></div>
      </div></div>
      ${docs.length ? `<div class="grid g-2">${docs.map((d) => {
        const sugg = d.predicted_category !== "unknown" ? d.predicted_category : "";
        const top = (d.probabilities || []).slice(0, 3);
        return `<div class="card review-card" id="rv-${d.id}">
          <div class="thumb">${isImg(d) ? `<img src="${API.fileUrl(d.id)}" alt="">` : extTag(d.file_ext)}</div>
          <div style="min-width:0">
            <div class="row"><b style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%">#${d.id} ${esc(d.filename)}</b></div>
            <div class="muted small">${fmtDate(d.created_at)} · ${esc(d.source)}</div>
            <div class="alerts" style="margin-top:8px">${(d.alerts || []).filter((a) => a.level !== "info").slice(0, 2).map((a) => `<div class="alert alert-${a.level}">${ICONS.alert}<span>${esc(a.message)}</span></div>`).join("")}</div>
            ${top.length ? `<div class="section-title" style="margin-top:12px">Model's top guesses</div>
              ${top.map((p) => `<div class="prob" style="grid-template-columns:130px 1fr 46px"><span class="small">${esc(catInfo(p.category).label)}</span><div class="track"><div class="fill" style="width:${p.probability * 100}%;background:${catColor(p.category)}"></div></div><span class="pct small">${pct(p.probability, 0)}</span></div>`).join("")}` :
              `<div class="muted small" style="margin-top:10px">No readable text, so no model guess.</div>`}
            <div class="row" style="margin-top:12px">
              <select id="reviewSelect-${d.id}">${options(sugg)}</select>
              <button class="btn btn-primary btn-sm" data-act="review" data-id="${d.id}">${ICONS.check} Assign</button>
              <button class="btn btn-sm" data-view="${d.id}">Details</button>
              <button class="btn btn-sm btn-danger" data-act="delete" data-id="${d.id}" title="Delete">${ICONS.trash}</button>
            </div>
          </div></div>`;
      }).join("")}</div>` : `<div class="card">${emptyState("Review queue is empty. Every document has been routed.", ICONS.check)}</div>`}`;

    bindDocActions(el, () => this.show(el));
    el.querySelectorAll("[data-view]").forEach((b) => (b.onclick = () => showDocument(b.dataset.view, () => this.show(el))));
  },
};
