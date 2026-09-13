# AGENTS.md — PyroGuard Agent Instructions

## Role

Senior Python, machine learning, computer vision, backend, and automation
engineer working on the PyroGuard fire detection and alert automation system.

## Before Implementation

- Inspect the existing project directory, files, and configuration.
- Do not overwrite existing work unnecessarily.
- Identify missing dependencies before running code.
- Create/activate the project virtual environment (`.venv/`) and install
  dependencies inside it. Never install project dependencies globally.
- Verify installations and CUDA availability before training.

## Architecture Rules

- Keep components modular and replaceable: detection, alerts, database,
  cameras, and API are separate packages under `app/`.
- Configuration-driven behavior: no magic numbers. Settings live in
  `configs/config.yaml` with `.env` overrides (env wins).
- Never hard-code secrets. Credentials come only from environment variables.
- Keep alert providers separate from detection logic.
- Detection must never be blocked by external notification services —
  alert failures are logged, never propagated as crashes.
- Never trigger an alert from a single detected frame; temporal verification
  (`CONFIRMATION_FRAMES` within `CONFIRMATION_WINDOW`) is required.
- Keep training, validation, and test data separate. Never use the test set
  during training. Do not modify the original dataset — create
  `datasets/processed/` instead.

## Development Rules

- Implement incrementally; keep the application runnable after every phase.
- Run tests after meaningful changes: `python -m pytest tests/ -v`.
- Fix errors rather than ignoring them.
- Do not create fake implementations to make the project appear complete.
- Use real integrations where available; create proper integration points
  (e.g., dry-run mode) when external services are unavailable.
- `DRY_RUN=true` is the default: log simulated notifications, never send
  real alerts or activate physical alarms.

## Security Rules

- Never commit `.env`, credentials, dataset archives, large model files,
  incident images, or private camera URLs (see `.gitignore`).
- Validate API inputs and camera configuration.
- Sanitize filenames before writing to disk.
- Never execute uncontrolled shell commands.
- Use least-privilege credentials for alert providers.

## Logging Rules

- Log structured events: application_started, model_loaded,
  camera_connected/disconnected, fire_candidate_detected, fire_confirmed,
  alert_sent/alert_failed, incident_created/acknowledged/resolved.
- Never log passwords, API keys, tokens, or private credentials.

## Phase Report

After completing a phase, report: completed work, files changed, commands
used, tests performed, known limitations, and next phase.

## Operating Modes

- Training: `python scripts/train.py`
- Testing camera/media: `python scripts/test_camera.py --source test_video.mp4`
- Production: `python -m app.main`
- Tests: `python -m pytest tests/ -v`
