import { useEffect, useState } from "react"
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
    play: <path d="m9 7 7 5-7 5V7Z" fill="currentColor" stroke="none" />,
    more: (
      <>
        <circle cx="5" cy="12" r="1" fill="currentColor" />
        <circle cx="12" cy="12" r="1" fill="currentColor" />
        <circle cx="19" cy="12" r="1" fill="currentColor" />
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

function AppShell() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("pyroguard-theme") === "dark",
  )
  useEffect(
    () => localStorage.setItem("pyroguard-theme", dark ? "dark" : "light"),
    [dark],
  )
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
          <span className="status-dot" />
          All systems nominal<small>4 camera feeds online</small>
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

function Dashboard() {
  const [acknowledged, setAcknowledged] = useState(false)
  const [camera, setCamera] = useState("North entrance")
  const [cameras, setCameras] = useState<{ id: string; name: string; status?: string; fps?: number }[]>([])
  const [feedOnline, setFeedOnline] = useState(true)
  const [fps, setFps] = useState("—")

  useEffect(() => {
    fetch("/cameras")
      .then((r) => r.json())
      .then((data) => {
        const list = Object.entries(data.cameras || {}).map(([id, cam]: [string, any]) => ({
          id,
          name: cam.name || id,
          status: cam.status,
          fps: cam.fps,
        }))
        setCameras(list)
        if (list.length > 0) setCamera(list[0].name)
        const live = list.find((c) => c.fps)
        if (live) setFps(String(live.fps))
      })
      .catch(() => setFeedOnline(false))
  }, [])

  const activeCam = cameras.find((c) => c.name === camera) || cameras[0] || { id: "CAM 01", name: camera, fps: 0 }
  const activeFps = activeCam.fps ? String(activeCam.fps) : fps
  const streamUrl = `/camera/stream?cam=${encodeURIComponent(activeCam.id || "camera_01")}&t=${Date.now()}`

  return (
    <main className="dashboard">
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">{new Date().toLocaleString("en-GB", { dateStyle: "full", timeStyle: "short" })}</p>
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
              <strong>{camera} · Warehouse A</strong>
            </div>
            <button className="feed-more" aria-label="Feed options">
              <Icon name="more" />
            </button>
          </div>
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
            <button className="play">
              <Icon name="play" />
            </button>
          </div>
          <div className="feed-footer">
            <div className="feed-tabs">
              {cameras.length > 0 ? (
                cameras.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setCamera(c.name)}
                    className={camera === c.name ? "selected" : ""}
                  >
                    {c.name}
                  </button>
                ))
              ) : (
                ["North entrance", "Loading bay", "Floor 2"].map((name) => (
                  <button
                    key={name}
                    onClick={() => setCamera(name)}
                    className={camera === name ? "selected" : ""}
                  >
                    {name}
                  </button>
                ))
              )}
            </div>
            <button className="text-action">Open feed →</button>
          </div>
        </article>
        <article className="prediction-card">
          <div className="card-icon">
            <Icon name="flame" />
          </div>
          <p className="eyebrow">Prediction result</p>
          <h2>Smoke detected</h2>
          <div className="score">
            <strong>94.8%</strong>
            <span>High confidence</span>
          </div>
          <div className="meter">
            <i />
          </div>
          <p className="prediction-note">
            A growing smoke plume was identified near the north entrance.
            Detection has persisted for 47 seconds.
          </p>
          <button className="dark-button">
            <Icon name="camera" />
            Review detection
          </button>
        </article>
      </section>
      <section className="secondary-grid">
        <article className={`alert-card ${acknowledged ? "acknowledged" : ""}`}>
          <div className="alert-icon">
            <Icon name={acknowledged ? "shield" : "bell"} />
          </div>
          <div className="alert-content">
            <p className="eyebrow">
              {acknowledged
                ? "Alert acknowledged"
                : "Alert status · action needed"}
            </p>
            <h2>
              {acknowledged
                ? "Notifications are being tracked"
                : "Smoke alert ready to send"}
            </h2>
            <p>
              {acknowledged
                ? "Administrators and on-site safety leads have received the incident record."
                : "Notify 3 administrators and 12 building occupants at Warehouse A with the camera location and predicted severity."}
            </p>
            {acknowledged && (
              <small>15 recipients notified · 14:32:18 UTC</small>
            )}
          </div>
          {!acknowledged && (
            <button
              onClick={() => setAcknowledged(true)}
              className="alert-button"
            >
              Send alert now
            </button>
          )}
        </article>
        <article className="coverage-card">
          <p className="eyebrow">Protection coverage</p>
          <div>
            <strong>04</strong>
            <span>
              of 04 feeds
              <br />
              connected
            </span>
          </div>
          <div className="coverage-bars">
            <i />
            <i />
            <i />
            <i />
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
