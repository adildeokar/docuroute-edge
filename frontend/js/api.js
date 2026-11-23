/* api.js - tiny wrapper around fetch() for the edge service REST API.
   The dashboard is served by the Flask edge service itself, so the base URL is the same origin.
   (If index.html is opened directly from disk, it falls back to http://localhost:5000.) */
const API_BASE = location.protocol === "file:" ? "http://localhost:5000" : "";

const API = {
  async request(method, path, body, isForm = false) {
    const opts = { method, headers: {} };
    if (body && isForm) opts.body = body;
    else if (body) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
    const res = await fetch(API_BASE + path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  },
  get: (path) => API.request("GET", path),
  post: (path, body) => API.request("POST", path, body || {}),
  del: (path) => API.request("DELETE", path),

  /** Upload one file (or text) to /api/classify */
  classifyFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("source", "dashboard");
    return API.request("POST", "/api/classify", fd, true);
  },
  classifyText(text) {
    const fd = new FormData();
    fd.append("text", text);
    return API.request("POST", "/api/classify", fd, true);
  },
  fileUrl: (id, download) => `${API_BASE}/api/documents/${id}/file${download ? "?download=1" : ""}`,
  sampleUrl: (path) => `${API_BASE}/api/samples/file?path=${encodeURIComponent(path)}`,
};
