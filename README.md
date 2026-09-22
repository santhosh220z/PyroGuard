# PyroGuard — AI Fire Detection & Alert Automation

PyroGuard is a modular, real-time fire and smoke detection system. It uses a
YOLO-based object detection model to detect fire and smoke from camera streams,
verifies detections across multiple frames to reduce false positives, captures
evidence, records incidents in a database, and triggers alerts automatically.

> **Safety notice**: PyroGuard is a prototype/portfolio project. It is **not** a
> certified fire-safety system. AI detection can produce false positives and
> false negatives. Real deployments should use certified smoke/heat detection
> hardware alongside (not instead of) this system.

## Features

- **Fire & smoke detection** — YOLO-based object detection with configurable
  confidence/IoU thresholds, image size, and device (GPU with CPU fallback).
- **Temporal verification** — fire is confirmed only after N detections within
  a time window, reducing false positives from single frames.
- **Alert automation** — pluggable providers (Email/SMTP, Telegram, Webhook)
  with alert cooldown, deduplication, and circuit-breaker protection.
- **Evidence capture** — snapshots, metadata, and event logs saved per incident.
- **Incident database** — SQLite storage with full incident lifecycle statuses.
- **Camera management** — multiple cameras (webcam, video file, RTSP) with
  health monitoring (status, FPS, failed-frame tracking).
- **REST API** — FastAPI endpoints for health, status, cameras, incidents,
  and model status.
- **Dry-run mode** — default ON: runs detection, captures evidence, creates
  incidents, and logs simulated notifications without sending real alerts.

## Project Structure

```
pyroguard/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/routes.py        # REST API endpoints
│   ├── detection/           # YOLO detection + temporal verification + pipeline
│   ├── alerts/              # Alert service (SMTP, Telegram, Webhook)
│   ├── cameras/             # Camera manager with health monitoring
│   ├── incidents/           # Incident DB + evidence capture
│   ├── config/              # Configuration (YAML + .env)
│   └── database/            # Database helpers
├── configs/config.yaml      # Application configuration
├── dashboard/               # Dashboard (planned)
├── data/incidents/          # Evidence and incident database (runtime)
├── datasets/raw/            # D-Fire raw dataset (not committed)
├── datasets/processed/      # Processed dataset (not committed)
├── models/                  # Trained model weights (not committed)
├── scripts/                 # Dataset prep, training, evaluation, camera test
├── tests/                   # Unit and integration tests
├── .env.example             # Environment variable template
└── requirements.txt
```

## Setup

1. **Create a virtual environment**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # Linux/macOS
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   For GPU acceleration, install the CUDA-enabled PyTorch build:
   https://pytorch.org/get-started/locally/

3. **Configure environment**

   ```bash
   copy .env.example .env        # Windows
   cp .env.example .env          # Linux/macOS
   ```

   Edit `.env` with your credentials. `DRY_RUN=true` (default) ensures no real
   alerts are sent. Never commit `.env`.

4. **Prepare the dataset (D-Fire)**

   Download D-Fire (https://github.com/gaia-solutions-on-demand/DFireDataset)
   and place it under `datasets/raw/` with the YOLO layout:

   ```
   datasets/raw/train/images/  datasets/raw/train/labels/
   datasets/raw/val/images/    datasets/raw/val/labels/
   datasets/raw/test/images/   datasets/raw/test/labels/
   ```

   Then validate it:

   ```bash
   python scripts/prepare_dataset.py
   ```

5. **Train the model**

   ```bash
   python scripts/train.py
   ```

   The best checkpoint is saved to `models/fire_smoke_yolo.pt`.

## Usage

- **Production API + detection**: `python -m app.main`
- **Testing on media**: `python scripts/test_camera.py --source test_video.mp4`
- **Evaluation**: `python scripts/evaluate.py`

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/status` | System status |
| GET | `/cameras` | Camera list with health |
| GET | `/incidents` | List incidents |
| GET | `/incidents/{id}` | Incident detail |
| POST | `/incidents/{id}/acknowledge` | Acknowledge incident |
| POST | `/incidents/{id}/resolve` | Resolve incident |
| GET | `/model/status` | Model status |

Interactive docs: `http://localhost:8000/docs`

### Real-time detection loop

```python
from app.detection.pipeline import run_pipeline
run_pipeline(camera_source=0, camera_id="camera_01", camera_name="Main Entrance")
```

Press `q` in the display window to stop.

## Configuration

Settings are centralized in `configs/config.yaml` and overridable via
environment variables (env vars take precedence). Secrets live only in `.env`.

Key settings: `MODEL_PATH`, `CONFIDENCE_THRESHOLD`, `IOU_THRESHOLD`,
`CONFIRMATION_FRAMES`, `CONFIRMATION_WINDOW`, `ALERT_COOLDOWN`,
`CAMERA_SOURCE`, `DATABASE_URL`, `LOG_LEVEL`, `DRY_RUN`.

## Testing

```bash
python -m pytest tests/ -v
```

## Incident Lifecycle

Statuses: `DETECTED → CONFIRMED → ALERT_SENT → ACKNOWLEDGED → RESOLVED`
(or `FALSE_POSITIVE`).

## License

For educational/portfolio use. See the D-Fire dataset license for data usage terms and the model i used is YOLOV11s.
