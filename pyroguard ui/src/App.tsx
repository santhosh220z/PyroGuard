import { useEffect, useRef, useState } from "react"
import {
  createBrowserRouter,
  Link,
  Navigate,
  Outlet,
  RouterProvider,
} from "react-router"

function Icon({ name, className = "" }: { name: string className?: string }) {
  const icons: Record<string, React.ReactNode> = {
    flame: (
      <path d="M12 21c4.1 0 7-2.7 7-6.5 0-3-1.8-5.5-4.2-7.8.1 2-1 3.5-2.3 4.4.1-3.7-1.8-6-3.7-7.9.1 3-2.5 5.6-3.6 8.2C3.2 16.6 6.8 21 12 21Zm0-2.5c-1.8 0-3-1.2-3-2.8 0-1.1.7-2.3 2-3.7.1 1.3.7 2 1.5 2.5.6-.5 1.1-1.2 1.4-2.2 1.3 1.3 1.8 2.4 1.8 3.4 0 1.7-1.4 2.8-3.7 2.8Z" />
    ),
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    camera: (
      <>
        <path d="M4 7.5h3l1.5-2h7l1.5 2H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z" />
        <circle cx="12" cy="14" r="3.5" />
      </>
    ),
    bell: (
      <>
        <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
      </>
    ),
    shield: (
      <path d="M12 3 4.5 6v5.4c0 4.7 3.2 8.7 7.5 9.6 4.3-.9 7.5-4.9 7.5-9.6V6L12 3Z" />
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="3.5" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </>
    ),
    moon: (
      <path d="M20.4 15.3A8.5 8.5 0 0 1 8.7 3.6 8.5 8.5 0 1 0 20.4 15.3Z" />
    ),
    more: (
      <>
        <circle cx="5" cy="12" r="1" fill="currentColor" />
        <circle cx="12" cy="12" r="1" fill="currentColor" />
        <circle cx="19" cy="12" r="1" fill="currentColor" />
      </>
    ),
    upload: (
      <>
        <path d="M12 16V4M12 4l-4 4M12 4l4 4" />
        <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
      </>
    ),
    flip: (
      <>
        <path d="M4 12a8 8 0 0 1 13.5-5.7L20 8" />
        <path d="M20 3v5h-5" />
        <path d="M20 12a8 8 0 0 1-13.5 5.7L4 16" />
        <path d="M4 21v-5h5" />
      </>
    ),
  }
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {icons[name]}
    </svg>
  )
}

async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

function AppShell() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("pyroguard-theme") === "dark",
  )
  const [cameras, setCameras] = useState<any>(null)

  useEffect(
    () => localStorage.setItem("pyroguard-theme", dark ? "dark" : "light"),
    [dark],
  )

  useEffect(() => {
    let alive = true
    const load = () =>
      fetchJSON<any>("/cameras").then((d) => {
        if (!alive || !d) return
        setCameras(d.cameras)
      })
    load()
    const t = setInterval(load, 5000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const camList = cameras ? Object.values(cameras as any) : []
  const camCount = camList.length
  const connected = camList.filter(
    (c: any) => c.status === "HEALTHY" || c.is_opened === true,
  ).length
  const allNominal = camCount > 0 && connected === camCount

  return (
    <div className={`app-shell ${dark ? "dark" : ""}`}>
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <Icon name="flame" />
          </span>
          <span>pyroguard</span>
        </Link>
        <div className="nav-caption">Workspace</div>
        <nav>
          <Link className="nav-link active" to="/">
            <Icon name="grid" />
            Dashboard
          </Link>
        </nav>
        <div className="sidebar-status">
          <span className={`status-dot ${allNominal ? "" : "warn"}`} />
          {allNominal ? "All systems nominal" : "Attention needed"}
          <small>
            {camCount > 0
              ? `${connected} of ${camCount} camera ${camCount === 1 ? "feed" : "feeds"} online`
              : "Connecting to cameras…"}
          </small>
        </div>
      </aside>
      <div className="page">
        <header className="topbar">
          <Link to="/" className="mobile-brand" aria-label="Pyroguard dashboard">
            <span className="brand-mark">
              <Icon name="flame" />
            </span>
            <span>pyroguard</span>
          </Link>
          <span className="eyebrow">Pyroguard monitoring</span>
          <div className="top-actions">
            <button
              onClick={() => setDark(!dark)}
              className="icon-button"
              aria-label="Toggle color theme"
              title={dark ? "Use light theme" : "Use dark theme"}
            >
              <Icon name={dark ? "sun" : "moon"} />
            </button>
            <button
              className="icon-button notification"
              aria-label="Notifications"
            >
              <Icon name="bell" />
            </button>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  )
}

function useClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return now
}

function Dashboard() {
  const now = useClock()

  const [camera, setCamera] = useState("")
  const [cameras, setCameras] = useState<{ id: string; name: string; status?: string; fps?: number; is_opened?: boolean; is_file_source?: boolean; source?: string }[]>([])
  const [feedOnline, setFeedOnline] = useState(true)
  const [streamToken, setStreamToken] = useState(0)
  const [feedMenuOpen, setFeedMenuOpen] = useState(false)
  const [demoUploading, setDemoUploading] = useState(false)
  const [demoUploaded, setDemoUploaded] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // live detection + incidents polling
  const [live, setLive] = useState<any>(null)
  const [incidents, setIncidents] = useState<any[]>([])
  const [acknowledgedId, setAcknowledgedId] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      const [cam, det, inc] = await Promise.all([
        fetchJSON<{ cameras: any }>("/cameras"),
        fetchJSON<any>("/detection/live"),
        fetchJSON<{ incidents: any[] }>("/incidents"),
      ])
      if (!alive) return

      if (cam?.cameras) {
        const list = Object.entries(cam.cameras).map(([id, c]: [string, any]) => ({
          id,
          name: c.name || id,
          status: c.status,
          fps: c.fps,
          is_opened: c.is_opened,
          is_file_source: c.is_file_source,
          source: c.source,
        }))
        setCameras(list)
        setCamera((prev) => prev || list[0]?.name || "")
      }
      setLive(det)
      setIncidents(inc?.incidents || [])
    }
    load()
    const t = setInterval(load, 2000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const switchCamera = (name: string) => {
    setCamera(name)
    setStreamToken((t) => t + 1)
  }

  const uploadDemoVideo = async (file: File) => {
    const fd = new FormData()
    fd.append("file", file)
    setDemoUploading(true)
    setUploadError(null)
    try {
      const res = await fetch("/camera/demo/upload", { method: "POST", body: fd })
      const data = await res.json().catch(() => null)
      if (!res.ok) {
        setUploadError(data?.detail || `Upload failed (${res.status})`)
        return
      }
      // switch to the demo feed so the new clip is visible immediately
      const demoCam = cameras.find((c) => c.is_file_source)
      if (demoCam) switchCamera(demoCam.name)
      else if (data?.camera_id) {
        const c = cameras.find((c) => c.id === data.camera_id)
        if (c) switchCamera(c.name)
      }
    } catch (err) {
      setUploadError(String(err))
    } finally {
      setDemoUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  // close the feed menu when clicking elsewhere
  useEffect(() => {
    if (!feedMenuOpen) return
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setFeedMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", onDown)
    return () => document.removeEventListener("mousedown", onDown)
  }, [feedMenuOpen])

  const activeCam = cameras.find((c) => c.name === camera) || cameras[0] || { id: "CAM 01", name: camera, fps: 0 }
  const activeFps = activeCam.fps ? String(activeCam.fps) : "—"
  const streamUrl = `/camera/stream?cam=${encodeURIComponent(activeCam.id || "camera_01")}&t=${streamToken}`

  // Live prediction data
  const liveCam: any = live?.cameras?.[activeCam.id || "camera_01"]
  const best = liveCam?.best_detection || null
  const predClass = best?.class || null
  const predConf = best ? Math.round(best.confidence * 1000) / 10 : 0
  const predState: string = liveCam?.state || "NORMAL"
  const persisted = liveCam?.persisted_seconds ?? null

  const predTitle =
    predClass === "fire"
      ? "Fire detected"
      : predClass === "smoke"
        ? "Smoke detected"
        : "No event"
  const predNote =
    predClass
      ? `${predClass[0].toUpperCase()}${predClass.slice(1)} detected at ${liveCam?.name || "the monitored area"}.`
          + (persisted != null ? ` Detection has persisted for ${persisted.toFixed(0)} s.` : "")
      : "Monitoring the live feed. No fire or smoke has been detected on this camera."
  const scoreLabel =
    predState === "FIRE_DETECTED"
      ? "Fire confirmed"
      : predState === "WARNING"
        ? "Candidate — verifying"
        : predClass
          ? "Confidence"
          : "No detection"

  // Alert card from real incidents
  const latestIncident: any = incidents[0] || null
  const isAcknowledged = acknowledgedId !== null || latestIncident?.status === "ACKNOWLEDGED"
  const hasAlert = live?.fire_confirmed === true || predState === "FIRE_DETECTED"

  const acknowledge = async () => {
    if (!latestIncident) return
    await fetchJSON(`/incidents/${latestIncident.incident_id}/acknowledge`)
    setAcknowledgedId(latestIncident.incident_id)
  }

  const coverageConnected = cameras.filter((c) => c.status === "HEALTHY" || c.is_opened).length
  const coverageTotal = cameras.length

  return (
    <main className="dashboard">
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">
            {now.toLocaleString("en-GB", { dateStyle: "full", timeStyle: "medium" })}
          </p>
          <h1>Detection overview</h1>
          <p className="subcopy">
            Live fire and smoke intelligence across your monitored spaces.
          </p>
        </div>
        <div className="live-status">
          <span className="pulse-dot" />
          Monitoring live
        </div>
      </div>
      <section className="primary-grid">
        <article className="feed-card">
          <div className="feed-header">
            <div>
              <p className="eyebrow">Live camera</p>
              <strong>{activeCam.name || camera}</strong>
            </div>
            <div className="feed-menu" ref={menuRef}>
              <button
                className={`feed-more ${feedMenuOpen ? "open" : ""}`}
                aria-label="Feed options"
                aria-expanded={feedMenuOpen}
                onClick={() => setFeedMenuOpen((o) => !o)}
              >
                <Icon name="more" />
              </button>
              {feedMenuOpen && (
                <div className="feed-menu-pop">
                  <button
                    className="feed-menu-item"
                    disabled={demoUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Icon name="upload" />
                    {demoUploading ? "Uploading demo video…" : "Upload demo video"}
                  </button>
                  <a
                    className="feed-menu-item"
                    href={`/camera/snapshot?cam=${encodeURIComponent(activeCam.id || "")}`}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => setFeedMenuOpen(false)}
                  >
                    <Icon name="camera" />
                    View snapshot
                  </a>
                  <a
                    className="feed-menu-item"
                    href={streamUrl}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => setFeedMenuOpen(false)}
                  >
                    <Icon name="flip" />
                    Open raw stream
                  </a>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) uploadDemoVideo(f)
                }}
              />
            </div>
          </div>
          {uploadError && !demoUploading && (
            <div className="feed-status error">
              <span>Demo upload failed · {uploadError}</span>
              <button onClick={() => setUploadError(null)}>Dismiss</button>
            </div>
          )}
          <div className="feed-visual">
            {feedOnline ? (
              <img
                src={streamUrl}
                alt="Live surveillance feed"
                onError={() => setFeedOnline(false)}
              />
            ) : (
              <div className="feed-offline">
                <p>Feed unavailable</p>
              </div>
            )}
            <div className="feed-overlay" />
            <div className="feed-labels">
              <span>{activeCam.id || "CAM 01"}</span>
              <span>{activeFps} FPS</span>
            </div>
          </div>
          <div className="feed-footer">
            <div className="feed-tabs">
              {cameras.length > 0 ? (
                cameras.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => switchCamera(c.name)}
                    className={camera === c.name ? "selected" : ""}
                  >
                    {c.name}
                  </button>
                ))
              ) : (
                <span className="feed-tabs-empty">Waiting for cameras…</span>
              )}
            </div>
            <a
              className="text-action"
              href={streamUrl}
              target="_blank"
              rel="noreferrer"
              onClick={() => setFeedMenuOpen(false)}
            >
              Open live stream →
            </a>
          </div>
        </article>
        <article className="prediction-card">
          <div className="card-icon">
            <Icon name="flame" />
          </div>
          <p className="eyebrow">Prediction result · {live?.model_loaded ? "live model" : "loading model…"}</p>
          <h2>{predTitle}</h2>
          <div className="score">
            <strong>{predClass ? `${predConf}%` : "—"}</strong>
            <span>{scoreLabel}</span>
          </div>
          <div className="meter">
            <i style={{ width: `${Math.min(predConf, 100)}%` }} />
          </div>
          <p className="prediction-note">{predNote}</p>
          <a className="dark-button" href="/camera/snapshot" target="_blank" rel="noreferrer">
            <Icon name="camera" />
            View snapshot
          </a>
        </article>
      </section>
      <section className="secondary-grid">
        <article className={`alert-card ${isAcknowledged ? "acknowledged" : ""}`}>
          <div className="alert-icon">
            <Icon name={isAcknowledged ? "shield" : hasAlert ? "bell" : "camera"} />
          </div>
          <div className="alert-content">
            <p className="eyebrow">
              {latestIncident
                ? `Latest incident · ${latestIncident.incident_id}`
                : hasAlert
                  ? "Alert status · action needed"
                  : "Alert status · all clear"}
            </p>
            <h2>
              {isAcknowledged
                ? "Incident acknowledged"
                : latestIncident
                  ? `${latestIncident.event_type} alert · ${Math.round((latestIncident.confidence || 0) * 100)}% confidence`
                  : hasAlert
                    ? "Fire confirmed — alert ready"
                    : "No active fire alerts"}
            </h2>
            <p>
              {latestIncident
                ? `Camera ${latestIncident.camera_id} · status ${latestIncident.status} · ${new Date(latestIncident.timestamp).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}`
                : hasAlert
                  ? "Fire metadata and incident record are ready to dispatch."
                  : "Monitoring is live. Alerts are dispatched automatically when fire is confirmed."}
            </p>
            {isAcknowledged && (
              <small>Acknowledged · {new Date().toLocaleTimeString("en-GB")}</small>
            )}
          </div>
          {!isAcknowledged && latestIncident && (
            <button onClick={acknowledge} className="alert-button">
              Acknowledge incident
            </button>
          )}
          {!isAcknowledged && !latestIncident && hasAlert && (
            <button onClick={acknowledge} className="alert-button" disabled>
              Dispatching…
            </button>
          )}
        </article>
        <article className="coverage-card">
          <p className="eyebrow">Protection coverage</p>
          <div>
            <strong>{String(coverageConnected).padStart(2, "0")}</strong>
            <span>
              of {String(coverageTotal).padStart(2, "0")} {coverageTotal === 1 ? "feed" : "feeds"}
              <br />
              connected
            </span>
          </div>
          <div className="coverage-bars">
            {Array.from({ length: Math.max(coverageTotal, 1) }).map((_, i) => (
              <i key={i} className={i < coverageConnected ? "" : "off"} />
            ))}
          </div>
        </article>
      </section>
    </main>
  )
}

const router = createBrowserRouter(
  [
    {
      Component: AppShell,
      children: [
        { index: true, Component: Dashboard },
        { path: "about", Component: () => <Navigate to="/" replace /> },
        { path: "*", Component: () => <Navigate to="/" replace /> },
      ],
    },
  ],
  { basename: "/dashboard" },
)
export default function App() {
  return <RouterProvider router={router} />
}