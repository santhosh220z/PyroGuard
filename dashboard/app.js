const API_BASE = location.protocol.startsWith("http") ? "" : "http://localhost:8000";
const REFRESH_MS = 5000;

const REFRESH_TOGGLE_LABELS = { pause: "Pause", resume: "Resume" };
const STATUS_BADGE_CLASS = {
  DETECTED: "badge-red",
  ACKNOWLEDGED: "badge-amber",
  RESOLVED: "badge-green",
  FALSE_POSITIVE: "badge-muted",
};

let paused = false;
let timer = null;

async function fetchJSON(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, { 
    headers: { Accept: "application/json" },
    ...options 
  });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

function setMetric(id, value, tone, sub) {
  const valueEl = document.getElementById(id);
  const subEl = document.getElementById(`${id}-sub`);
  valueEl.textContent = value;
  valueEl.classList.remove("ok", "warn", "bad");
  if (tone) valueEl.classList.add(tone);
  if (sub !== undefined) subEl.textContent = sub;
}

function renderStatus(data) {
  setMetric("metric-service", data.status || "unknown", "ok", `threshold ${data.confidence_threshold ?? "—"}`);
  const dryRunBadge = document.getElementById("dry-run-badge");
  dryRunBadge.classList.toggle("hidden", !data.dry_run);
  const footer = document.getElementById("footer-info");
  footer.textContent = `PyroGuard API · model ${data.model ?? "—"} · confidence threshold ${data.confidence_threshold ?? "—"}`;
}

function renderModel(data) {
  const tone = data.loaded ? (data.fire_confirmed ? "bad" : "ok") : "warn";
  const value = data.fire_confirmed ? "FIRE" : data.loaded ? "Armed" : "Missing";
  const info = data.confirmation_info || {};
  const sub = data.loaded
    ? `confirmation ${info.confirmation_counter ?? 0}/3 · history ${info.history_length ?? 0}`
    : data.model_path;
  setMetric("metric-detection", value, tone, sub);
  setMetric("metric-model", data.loaded ? "Loaded" : "Not found", data.loaded ? "ok" : "warn", data.model_path);
}

function renderCameras(payload) {
  const grid = document.getElementById("cameras-grid");
  grid.textContent = "";
  const cameras = Object.entries(payload.cameras || {});
  if (!cameras.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No cameras configured";
    grid.appendChild(empty);
    return;
  }
  for (const [id, cam] of cameras) {
    const card = document.createElement("article");
    card.className = "card camera-card";
    card.setAttribute("data-stagger", "");

    const head = document.createElement("div");
    head.className = "camera-head";
    const name = document.createElement("span");
    name.className = "camera-name";
    name.textContent = cam.name || id;
    const badge = document.createElement("span");
    badge.className = `badge ${cam.status === "HEALTHY" ? "badge-green" : cam.status === "WARNING" ? "badge-amber" : "badge-red"}`;
    badge.textContent = cam.status || "UNKNOWN";
    head.append(name, badge);

    const meta = document.createElement("p");
    meta.className = "camera-meta";
    meta.textContent = `${id} · ${cam.enabled ? "enabled" : "disabled"} · failed frames ${cam.failed_frames ?? 0}`;

    card.append(head, meta);
    grid.appendChild(card);
  }
}

function renderIncidents(payload) {
  const body = document.getElementById("incidents-body");
  body.textContent = "";
  const incidents = payload.incidents || [];
  const open = incidents.filter((i) => i.status === "DETECTED").length;
  const acknowledged = incidents.filter((i) => i.status === "ACKNOWLEDGED").length;
  setMetric(
    "metric-incidents",
    String(incidents.length),
    open > 0 ? "bad" : "ok",
    `${open} open · ${acknowledged} acknowledged`
  );
  if (!incidents.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 6;
    cell.className = "empty-state";
    cell.textContent = "No incidents recorded";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }
  for (const incident of incidents) {
    body.appendChild(incidentRow(incident));
  }
}

function incidentRow(incident) {
  const row = document.createElement("tr");

  const idCell = document.createElement("td");
  const idSpan = document.createElement("span");
  idSpan.className = "incident-id";
  idSpan.textContent = incident.incident_id;
  idCell.appendChild(idSpan);

  const timeCell = document.createElement("td");
  timeCell.className = "incident-time";
  timeCell.textContent = formatTime(incident.timestamp);

  const cameraCell = document.createElement("td");
  cameraCell.textContent = incident.camera_id;

  const eventCell = document.createElement("td");
  eventCell.textContent = incident.event_type;

  const confidenceCell = document.createElement("td");
  confidenceCell.className = "confidence-cell";
  confidenceCell.textContent = incident.confidence != null ? Number(incident.confidence).toFixed(2) : "—";

  const statusCell = document.createElement("td");
  const statusBadge = document.createElement("span");
  statusBadge.className = `badge ${STATUS_BADGE_CLASS[incident.status] || "badge-muted"}`;
  statusBadge.textContent = incident.status;
  statusCell.appendChild(statusBadge);

  const actionsCell = document.createElement("td");
  actionsCell.className = "actions-cell";
  if (incident.status === "DETECTED") {
    actionsCell.appendChild(actionButton("Acknowledge", "btn-accent", incident.incident_id, "acknowledge"));
  }
  if (incident.status === "DETECTED" || incident.status === "ACKNOWLEDGED") {
    actionsCell.appendChild(actionButton("Resolve", "btn-danger", incident.incident_id, "resolve"));
  }

  row.append(idCell, timeCell, cameraCell, eventCell, confidenceCell, statusCell, actionsCell);
  return row;
}

function actionButton(label, cssClass, incidentId, action) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `btn ${cssClass}`;
  button.textContent = label;
  button.setAttribute("aria-label", `${label} incident ${incidentId}`);
  button.addEventListener("click", async () => {
    button.disabled = true;
    const original = button.textContent;
    button.textContent = "Working…";
    try {
      await fetchJSON(`/incidents/${encodeURIComponent(incidentId)}/${action}`, { method: "POST" });
      showToast(`${label}d ${incidentId}`, false);
      await refresh(true);
    } catch (err) {
      button.disabled = false;
      button.textContent = original;
      showToast(`Failed to ${action} ${incidentId}`, true);
    }
  });
  return button;
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function showToast(message, isError) {
  const region = document.getElementById("toast-region");
  const toast = document.createElement("div");
  toast.className = `toast${isError ? " toast-error" : ""}`;
  toast.textContent = message;
  region.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function setLiveBadge(state, text) {
  const badge = document.getElementById("live-badge");
  badge.classList.remove("badge-green", "badge-red", "badge-amber");
  badge.classList.add(state);
  document.getElementById("live-text").textContent = text;
}

async function refresh(manual = false) {
  try {
    const [health, status, cameras, incidents, model] = await Promise.all([
      fetchJSON("/health"),
      fetchJSON("/status"),
      fetchJSON("/cameras"),
      fetchJSON("/incidents"),
      fetchJSON("/model/status"),
    ]);
    renderStatus({ ...status, ...health });
    renderModel(model);
    renderCameras(cameras);
    renderIncidents(incidents);
    setLiveBadge("badge-green", paused ? "Live (paused)" : "Live");
  } catch (err) {
    setLiveBadge("badge-red", "API unreachable");
    if (manual) showToast("Could not reach the API", true);
  }
}

function scheduleRefresh() {
  clearInterval(timer);
  timer = setInterval(() => {
    if (!paused) refresh();
  }, REFRESH_MS);
}

const toggleButton = document.getElementById("refresh-toggle");
toggleButton.addEventListener("click", () => {
  paused = !paused;
  toggleButton.setAttribute("aria-pressed", String(paused));
  toggleButton.setAttribute("aria-label", paused ? "Resume automatic refresh" : "Pause automatic refresh");
  document.getElementById("refresh-toggle-text").textContent = REFRESH_TOGGLE_LABELS[paused ? "resume" : "pause"];
  const text = document.getElementById("live-text");
  if (paused && text.textContent.startsWith("Live")) text.textContent = "Live (paused)";
  if (!paused) refresh();
});

document.addEventListener("DOMContentLoaded", async () => {
  const cards = document.querySelectorAll("[data-stagger]");
  cards.forEach((card, index) => {
    card.style.opacity = "0";
    card.style.transform = "translateY(16px) scale(0.96)";
    card.style.transition = `opacity 400ms cubic-bezier(0.34, 1.56, 0.64, 1) ${index * 60}ms, transform 400ms cubic-bezier(0.34, 1.56, 0.64, 1) ${index * 60}ms`;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      card.style.opacity = "1";
      card.style.transform = "translateY(0) scale(1)";
    }));
  });
  await refresh(true);
  scheduleRefresh();
});
