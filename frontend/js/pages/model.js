/* Model & Analytics page - how the ML model was trained and how well it performs. */
Pages.model = {
  title: "Model & Analytics",
  subtitle: "Training data, algorithm comparison, evaluation metrics and retraining",

  async show(el) {
    const m = await API.get("/api/model");
    const labels = m.classes.map((c) => catInfo(c).label);
    const kpi = (label, value, sub) => `<div class="card kpi"><div class="kpi-label">${label}</div><div class="kpi-value" style="font-size:24px">${value}</div><div class="kpi-sub">${sub}</div></div>`;
    const e2e = m.end_to_end;
    const bySrc = m.test_accuracy_by_source || {}, gen = m.synthetic_only_on_real;
    const realTotal = (m.dataset.per_source || {}).kaggle || 0;

    // confusion matrix as a heat-map table (sequential blue)
    const maxCell = Math.max(...m.confusion_matrix.flat());
    const cell = (v, diag) => {
      const t = v / maxCell;
      const bg = v === 0 ? "var(--surface-2)" : diag ? `rgba(42,120,214,${0.25 + t * 0.75})` : `rgba(235,104,52,${0.3 + t * 0.7})`;
      return `<td class="cell" style="background:${bg};color:${t > 0.5 && diag ? "#fff" : "var(--text)"}" title="${v} documents">${v}</td>`;
    };

    el.innerHTML = `
      <div class="grid g-6">
        ${kpi("Selected algorithm", `<span style="font-size:17px">${esc(m.model_name)}</span>`, `version ${m.version} · ${fmtDate(m.trained_at)}`)}
        ${kpi("Test accuracy", pct(m.test_accuracy, 2), `on ${m.dataset.test_size} unseen documents`)}
        ${kpi("Macro F1-score", pct(m.test_macro_f1, 2), "balanced over all 8 classes")}
        ${kpi("5-fold cross-validation", pct(m.cv_accuracy_mean, 2), `± ${pct(m.cv_accuracy_std, 2)} std`)}
        ${kpi("Training data", m.dataset.total, `${m.dataset.train_size} train / ${m.dataset.test_size} test · +${m.dataset.feedback_samples} feedback`)}
        ${kpi("Features", m.feature_count.toLocaleString(), "word + character TF-IDF")}
      </div>

      ${e2e ? `<div class="card mt"><div class="card-head"><h3>End-to-end test on scanned images (OCR + model)</h3><span class="muted">${fmtDate(e2e.tested_at)} · backend/test_system.py</span></div>
        <div class="grid g-4">
          <div><div class="muted small">Images tested</div><div class="kpi-value" style="margin-top:2px">${e2e.images}</div></div>
          <div><div class="muted small">Correctly classified</div><div class="kpi-value" style="margin-top:2px">${pct(e2e.accuracy, 1)}</div></div>
          <div><div class="muted small">Avg OCR time / image</div><div class="kpi-value" style="margin-top:2px">${fmtMs(e2e.avg_ocr_ms)}</div></div>
          <div><div class="muted small">Avg ML time / doc</div><div class="kpi-value" style="margin-top:2px">${fmtMs(e2e.avg_classify_ms)}</div></div>
        </div></div>` : ""}

      ${realTotal ? `<div class="card mt"><div class="card-head"><h3>Real-world validation (public Kaggle datasets)</h3><span class="muted">backend/kaggle_dataset.py</span></div>
        <div class="grid g-4">
          <div><div class="muted small">Real documents in training data</div><div class="kpi-value" style="margin-top:2px">${realTotal.toLocaleString()}</div><div class="kpi-sub">of ${m.dataset.total.toLocaleString()} · 5 categories</div></div>
          <div><div class="muted small">Test accuracy: real documents</div><div class="kpi-value" style="margin-top:2px">${bySrc.kaggle ? pct(bySrc.kaggle.accuracy, 1) : "-"}</div><div class="kpi-sub">${bySrc.kaggle ? bySrc.kaggle.documents + " unseen real docs" : ""}</div></div>
          <div><div class="muted small">Test accuracy: synthetic documents</div><div class="kpi-value" style="margin-top:2px">${bySrc.synthetic ? pct(bySrc.synthetic.accuracy, 1) : "-"}</div><div class="kpi-sub">${bySrc.synthetic ? bySrc.synthetic.documents + " unseen synthetic docs" : ""}</div></div>
          <div><div class="muted small">Synthetic-only model on real docs</div><div class="kpi-value" style="margin-top:2px">${gen ? pct(gen.accuracy, 1) : "-"}</div><div class="kpi-sub">${gen ? `trained without any real data, tested on ${gen.documents.toLocaleString()}` : ""}</div></div>
        </div>
        <div class="muted small mt">Receipts (SROIE), invoices, resumes, medical reports (mtsamples) and contracts (CUAD) include real documents. ID documents, bank statements and application forms are private, so no public dataset exists and they remain synthetic.</div></div>` : ""}

      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Algorithm comparison</h3><span class="muted">test error rate · lower is better</span></div>
          <div class="chart-box sm"><canvas id="chModels"></canvas></div>
          <div class="table-wrap mt"><table><thead><tr><th>Model</th><th>Accuracy</th><th>Macro F1</th><th>Train time</th><th>Predict / doc</th></tr></thead><tbody>
            ${m.model_comparison.map((r) => `<tr><td><b>${esc(r.model)}</b> ${r.model === m.model_name ? '<span class="status st-auto_routed">selected</span>' : ""}</td>
              <td>${pct(r.accuracy, 2)}</td><td>${pct(r.macro_f1, 2)}</td><td>${r.train_time_s}s</td><td>${r.predict_ms_per_doc} ms</td></tr>`).join("")}
          </tbody></table></div></div>
        <div class="card"><div class="card-head"><h3>Per-class performance</h3><span class="muted">test set</span></div>
          <div class="table-wrap"><table><thead><tr><th>Category</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>
            ${m.classes.map((c) => { const r = m.per_class[c]; return `<tr><td>${catBadge(c)}</td><td>${pct(r.precision, 1)}</td><td>${pct(r.recall, 1)}</td>
              <td>${confBar(r["f1-score"])}</td><td class="muted">${r.support}</td></tr>`; }).join("")}
          </tbody></table></div></div>
      </div>

      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Confusion matrix</h3><span class="muted">rows = true · columns = predicted</span></div>
          <div class="table-wrap"><table class="cm"><tr><th></th>${labels.map((l) => `<th class="col">${esc(l)}</th>`).join("")}</tr>
            ${m.confusion_matrix.map((row, i) => `<tr><th style="text-align:right">${esc(labels[i])}</th>${row.map((v, j) => cell(v, i === j)).join("")}</tr>`).join("")}
          </table></div>
          <div class="muted small mt">Blue diagonal = correct predictions. Orange off-diagonal cells = confusions, usually documents that share vocabulary (forms, contracts, statements). Examples are listed at the bottom of this page.</div></div>
        <div class="card"><div class="card-head"><h3>What the model learned</h3><span class="muted">strongest words per class</span></div>
          ${Object.entries(m.top_keywords || {}).map(([c, words]) => `<div class="kw-row"><div>${catBadge(c)}</div><div class="terms">${words.slice(0, 7).map((w) => `<span class="term">${esc(w)}</span>`).join("")}</div></div>`).join("") || '<div class="muted">Keyword weights not available for this model type.</div>'}
        </div>
      </div>

      <div class="grid g-2 mt">
        <div class="card"><div class="card-head"><h3>Continuous learning</h3><span class="muted">human-in-the-loop</span></div>
          <p style="margin-top:0">Documents confirmed or corrected in the <a href="#review">Review Queue</a> are added to the training set. Retraining runs locally on the edge device and the new model is hot-swapped without restarting the service.</p>
          <div class="row"><span class="badge">${m.available_feedback} human-verified document(s) available</span><span class="spacer"></span>
            <button class="btn btn-primary" id="retrainBtn">${ICONS.brain} Retrain model now</button></div>
          <div id="retrainMsg" class="mt"></div></div>
        <div class="card"><div class="card-head"><h3>Dataset (training corpus)</h3><span class="muted">data/dataset/documents.csv</span></div>
          <div class="chart-box sm"><canvas id="chDataset"></canvas></div></div>
      </div>

      ${(m.misclassified_examples || []).length ? `<div class="card mt"><div class="card-head"><h3>Examples the model got wrong (test set)</h3><span class="muted">used to discuss limitations</span></div>
        <div class="table-wrap"><table><thead><tr><th>True</th><th>Predicted</th><th>Source</th><th>Text snippet (pre-processed)</th></tr></thead><tbody>
        ${m.misclassified_examples.map((x) => `<tr><td>${catBadge(x.true)}</td><td>${catBadge(x.predicted)}</td><td class="small">${x.source === "kaggle" ? "real (Kaggle)" : esc(x.source || "synthetic")}</td><td class="mono small muted">${esc(x.snippet)}…</td></tr>`).join("")}
        </tbody></table></div></div>` : ""}`;

    makeChart("chModels", {
      type: "bar",
      data: { labels: m.model_comparison.map((r) => r.model),
        datasets: [{ label: "Error rate (100% - accuracy)", data: m.model_comparison.map((r) => +(100 - r.accuracy * 100).toFixed(2)),
          backgroundColor: m.model_comparison.map((r) => (r.model === m.model_name ? "#2a78d6" : "#86b6ef")), borderRadius: 4, maxBarThickness: 56 }] },
      options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `Error rate: ${c.parsed.y}%` } } },
        scales: { y: { beginAtZero: true, ticks: { callback: (v) => v + "%" } }, x: { grid: { display: false } } } },
    });
    // stacked bar: real (Kaggle) vs synthetic documents per category
    const realPer = m.dataset.real_per_class || {};
    const gap = getComputedStyle(document.body).getPropertyValue("--surface").trim() || "#fff";
    makeChart("chDataset", {
      type: "bar",
      data: { labels, datasets: [
        { label: "Real (Kaggle)", data: m.classes.map((c) => realPer[c] || 0), backgroundColor: "#2a78d6", borderColor: gap, borderWidth: { right: 2 }, barThickness: 14 },
        { label: "Synthetic / feedback", data: m.classes.map((c) => m.dataset.per_class[c] - (realPer[c] || 0)), backgroundColor: "#eb6834", borderRadius: { topRight: 4, bottomRight: 4 }, borderSkipped: false, barThickness: 14 },
      ] },
      options: { indexAxis: "y", plugins: { legend: { display: true, position: "bottom" } },
        scales: { x: { stacked: true, beginAtZero: true }, y: { stacked: true, grid: { display: false } } } },
    });

    el.querySelector("#retrainBtn").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Training 3 models + cross-validation…';
      try {
        const r = await API.post("/api/model/retrain");
        toast(r.message, "ok");
        loadHealth();
        this.show(el);
      } catch (err) {
        toast(err.message, "err");
        btn.disabled = false;
        btn.innerHTML = `${ICONS.brain} Retrain model now`;
      }
    };
  },
};
