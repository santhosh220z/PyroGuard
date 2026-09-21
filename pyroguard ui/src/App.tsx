import { useEffect, useState } from "react"
import {
  createBrowserRouter,
  Link,
  Navigate,
  Outlet,
  RouterProvider,
} from "react-router"

function Icon({ name, className = "" }: { name: string; className?: string }) {
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
    sun: (
      <>
        <circle cx="12" cy="12" r="3.5" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </>
    ),
    moon: (
      <path d="M20.4 15.3A8.5 8.5 0 0 1 8.7 3.6 8.5 8.5 0 1 0 20.4 15.3Z" />
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4.5 20c1.4-3.6 4.2-5.5 7.5-5.5s6.1 1.9 7.5 5.5" />
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
          <Link className="nav-link" to="/profile">
            <Icon name="user" />
            Profile
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
          <span className="eyebrow">Fire & smoke detection</span>
          <div className="top-actions">
            <Link
              to="/profile"
              className="icon-button"
              aria-label="Alert profile"
              title="Alert profile"
            >
              <Icon name="user" />
            </Link>
            <button
              onClick={() => setDark(!dark)}
              className="icon-button"
              aria-label="Toggle color theme"
              title={dark ? "Use light theme" : "Use dark theme"}
            >
              <Icon name={dark ? "sun" : "moon"} />
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
  const [cameras, setCameras] = useState<{ id: string; name: string; status?: string; fps?: number; is_opened?: boolean }[]>([])
  const [feedOnline, setFeedOnline] = useState(true)
  const [streamToken, setStreamToken] = useState(0)

  // live detection polling
  const [live, setLive] = useState<any>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      const [cam, det] = await Promise.all([
        fetchJSON<{ cameras: any }>("/cameras"),
        fetchJSON<any>("/detection/live"),
      ])
      if (!alive) return

      if (cam?.cameras) {
        const list = Object.entries(cam.cameras).map(([id, c]: [string, any]) => ({
          id,
          name: c.name || id,
          status: c.status,
          fps: c.fps,
          is_opened: c.is_opened,
        }))
        setCameras(list)
        setCamera((prev) => prev || list[0]?.name || "")
      }
      setLive(det)
    }
    load()
    const t = setInterval(load, 2000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const activeCam = cameras[0] || { id: "camera_01", name: camera, fps: 0 }
  const activeFps = activeCam.fps ? String(activeCam.fps) : "—"
  const streamUrl = `/camera/stream?cam=${encodeURIComponent(activeCam.id)}&t=${streamToken}`
  const retryFeed = () => {
    setFeedOnline(true)
    setStreamToken((t) => t + 1)
  }

  // Live prediction data
  const liveCam: any = live?.cameras?.[activeCam.id]
  const best = liveCam?.best_detection || null
  const predClass = best?.class || null
  const predConf = best ? Math.round(best.confidence * 1000) / 10 : 0
  const predState: string = liveCam?.state || "NORMAL"

  const predTitle =
    predClass === "fire"
      ? "Fire detected"
      : predClass === "smoke"
        ? "Smoke detected"
        : "No event"
  const predNote = predClass
    ? `${predClass[0].toUpperCase()}${predClass.slice(1)} detected at ${liveCam?.name || "the monitored area"}.`
    : "Monitoring the live feed. No fire or smoke has been detected."
  const scoreLabel =
    predState === "FIRE_DETECTED"
      ? "Fire confirmed"
      : predState === "WARNING"
        ? "Candidate — verifying"
        : predClass
          ? "Confidence"
          : "No detection"

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
            Live fire and smoke detection on your monitored camera feed.
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
                <button onClick={retryFeed}>Retry</button>
              </div>
            )}
            <div className="feed-overlay" />
            <div className="feed-labels">
              <span>{activeCam.id}</span>
              <span>{activeFps} FPS</span>
            </div>
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
        </article>
      </section>
      <section className="secondary-grid">
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

type ProfileData = {
  configured: boolean
  display_name: string | null
  email: string | null
  notify_email: boolean
  phone: string | null
  notify_sms: boolean
  telegram_chat_id: string | null
  notify_telegram: boolean
  resend_configured: boolean
  resend_from: string | null
  has_pin: boolean
  updated_at: string | null
}

function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null)
  const [form, setForm] = useState({
    display_name: "",
    email: "",
    notify_email: true,
    phone: "",
    notify_sms: false,
    telegram_chat_id: "",
    notify_telegram: false,
    resend_api_key: "",
    resend_from: "",
    pin: "",
    new_pin: "",
  })
  const [hasPin, setHasPin] = useState(false)
  const [resendConfigured, setResendConfigured] = useState(false)
  const [testingResend, setTestingResend] = useState(false)
  const [resendTest, setResendTest] = useState<{ kind: "ok" | "error"; text: string } | null>(null)

  useEffect(() => {
    let alive = true
    fetchJSON<ProfileData>("/api/profile").then((d) => {
      if (!alive) return
      setLoading(false)
      if (!d) {
        setMessage({ kind: "error", text: "Could not load profile. Is the server running?" })
        return
      }
      setHasPin(d.has_pin)
      setResendConfigured(d.resend_configured)
      setForm((f) => ({
        ...f,
        display_name: d.display_name || "",
        email: d.email || "",
        notify_email: d.notify_email,
        phone: d.phone || "",
        notify_sms: d.notify_sms,
        telegram_chat_id: d.telegram_chat_id || "",
        notify_telegram: d.notify_telegram,
        resend_from: d.resend_from || "",
      }))
    })
    return () => {
      alive = false
    }
  }, [])

  const set = (key: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value
    setForm((f) => ({ ...f, [key]: value }))
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: form.display_name || null,
          email: form.email || null,
          notify_email: form.notify_email,
          phone: form.phone || null,
          notify_sms: form.notify_sms,
          telegram_chat_id: form.telegram_chat_id || null,
          notify_telegram: form.notify_telegram,
          resend_api_key: form.resend_api_key.trim() || null,
          resend_from: form.resend_from.trim() || null,
          pin: form.pin || null,
          new_pin: form.new_pin || null,
        }),
      })
      const data = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = (data as any)?.detail
        const text = Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join("; ")
          : typeof detail === "string"
            ? detail
            : "Could not save profile"
        setMessage({ kind: "error", text })
        return
      }
      setHasPin(!!(data as ProfileData)?.has_pin)
      setResendConfigured(!!(data as ProfileData)?.resend_configured)
      setForm((f) => ({ ...f, pin: "", new_pin: "", resend_api_key: "" }))
      setMessage({ kind: "ok", text: "Profile saved. Fire alerts will use these contacts." })
    } catch {
      setMessage({ kind: "error", text: "Could not save profile. Is the server running?" })
    } finally {
      setSaving(false)
    }
  }

  const testResend = async () => {
    setTestingResend(true)
    setResendTest(null)
    try {
      const res = await fetch("/api/profile/resend/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: form.pin || null }),
      })
      const data = await res.json().catch(() => null)
      if (!res.ok) {
        const detail = (data as any)?.detail
        setResendTest({
          kind: "error",
          text: typeof detail === "string" ? detail : "Send test failed",
        })
        return
      }
      if ((data as any)?.success) {
        setResendTest({
          kind: "ok",
          text: `Test email sent to ${(data as any)?.recipient || "your address"}. Check your inbox.`,
        })
      } else {
        setResendTest({ kind: "error", text: (data as any)?.error || "Send test failed" })
      }
    } catch {
      setResendTest({ kind: "error", text: "Could not reach the server." })
    } finally {
      setTestingResend(false)
    }
  }

  return (
    <main className="dashboard">
      <div className="dashboard-head">
        <div>
          <p className="eyebrow">Alert contacts</p>
          <h1>Profile</h1>
          <p className="subcopy">
            Fire and smoke alerts are sent to these contacts. No login needed.
          </p>
        </div>
      </div>
      <section className="primary-grid">
        <article className="prediction-card">
          <div className="card-icon">
            <Icon name="user" />
          </div>
          <p className="eyebrow">Where alerts go</p>
          {loading ? (
            <p className="prediction-note">Loading profile…</p>
          ) : (
            <form onSubmit={save} className="profile-form">
              <label className="field">
                <span>Name</span>
                <input
                  type="text"
                  value={form.display_name}
                  onChange={set("display_name")}
                  placeholder="e.g. Home, Warehouse"
                  maxLength={128}
                />
              </label>
              <label className="field">
                <span>Email for alerts</span>
                <input
                  type="email"
                  value={form.email}
                  onChange={set("email")}
                  placeholder="you@example.com"
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={form.notify_email}
                  onChange={set("notify_email")}
                />
                Send email alerts
              </label>
              <label className="field">
                <span>Mobile number for SMS</span>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={set("phone")}
                  placeholder="+15551234567"
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={form.notify_sms}
                  onChange={set("notify_sms")}
                />
                Send SMS alerts
              </label>
              <label className="field">
                <span>Telegram chat ID</span>
                <input
                  type="text"
                  value={form.telegram_chat_id}
                  onChange={set("telegram_chat_id")}
                  placeholder="e.g. 123456789"
                  maxLength={64}
                />
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={form.notify_telegram}
                  onChange={set("notify_telegram")}
                />
                Send Telegram alerts
              </label>
              <div className="field">
                <span>
                  Resend API key{" "}
                  {resendConfigured ? (
                    <em className="resend-saved">· key saved</em>
                  ) : (
                    <em className="resend-muted">· optional — enables Resend email alerts</em>
                  )}
                </span>
                <input
                  type="password"
                  value={form.resend_api_key}
                  onChange={set("resend_api_key")}
                  placeholder={resendConfigured ? "••••••••••••••• (leave blank to keep)" : "re_…"}
                  maxLength={128}
                  autoComplete="off"
                />
              </div>
              <label className="field">
                <span>Verified sender</span>
                <input
                  type="email"
                  value={form.resend_from}
                  onChange={set("resend_from")}
                  placeholder="alerts@yourdomain.com"
                />
              </label>
              <div className="resend-actions">
                <button
                  type="button"
                  className="profile-save"
                  onClick={testResend}
                  disabled={testingResend || !resendConfigured}
                  title={
                    resendConfigured
                      ? "Send a test email to verify Resend"
                      : "Save a Resend API key and verified sender first"
                  }
                >
                  {testingResend ? "Sending test…" : "Send test email"}
                </button>
                {resendTest && (
                  <p className={resendTest.kind === "ok" ? "form-ok" : "form-error"}>
                    {resendTest.text}
                  </p>
                )}
              </div>
              <label className="field">
                <span>{hasPin ? "Current PIN (required to save)" : "Current PIN (only if one is set)"}</span>
                <input
                  type="password"
                  value={form.pin}
                  onChange={set("pin")}
                  placeholder="••••"
                  autoComplete="off"
                />
              </label>
              <label className="field">
                <span>New PIN (optional, min 4 chars)</span>
                <input
                  type="password"
                  value={form.new_pin}
                  onChange={set("new_pin")}
                  placeholder="Set a PIN to lock edits"
                  autoComplete="off"
                />
              </label>
              <button type="submit" className="profile-save" disabled={saving}>
                {saving ? "Saving…" : "Save profile"}
              </button>
              {message && (
                <p className={message.kind === "ok" ? "form-ok" : "form-error"}>
                  {message.text}
                </p>
              )}
            </form>
          )}
        </article>
        <article className="coverage-card">
          <p className="eyebrow">How it works</p>
          <div>
            <strong>01</strong>
            <span>
              Save your email and mobile number here.
              <br />
              No account needed.
            </span>
          </div>
          <p className="prediction-note">
            When fire or smoke is confirmed, PyroGuard sends alerts to the
            contacts you enabled above. Email and Telegram need their server
            credentials configured; SMS needs a Twilio account or webhook.
            For Resend, save your API key and a verified sender here, then use
            "Send test email" to verify before fire alerts rely on it.
          </p>
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
        { path: "profile", Component: ProfilePage },
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
