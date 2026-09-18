# LinkedIn post for PyroGuard (v2)

## Main post (copy-paste ready, plain text — LinkedIn doesn't render markdown)

The hardest part of building a fire detection AI wasn't detecting fire. It was teaching it not to cry wolf.

For the past few weeks I've been building PyroGuard, a real-time fire and smoke detection system: a YOLO11n model I trained on the D-Fire dataset, watching camera streams and deciding what's actually worth waking someone up for.

The demo version is easy. Draw boxes on flames, post the video, collect the likes. But a single smoky frame can look exactly like fire, and one false alarm at 3am is how a monitoring system loses everyone's trust.

That's why the pipeline never trusts a single frame:

→ YOLO flags fire or smoke on every frame
→ Nothing gets confirmed until 3 detections land within 5 seconds
→ Only then: evidence snapshot saved, incident written to SQLite, alert fired through email, Telegram, or a webhook
→ Alerts have cooldown, deduplication, and a circuit breaker, because notification services fail in creative ways

Every incident carries a full lifecycle: detected, confirmed, alert sent, acknowledged, resolved. Or marked as a false positive, which matters just as much.

Honest numbers from the test set: 0.77 precision, 0.69 recall, 0.77 mAP50. A nano model gets you surprisingly far, but this is nowhere near certified-safety grade and I'm not pretending otherwise. It ships in dry-run mode by default for the same reason: until you flip the switch, it logs what it would have alerted instead of actually alerting.

The model was the fun part. The plumbing around it (alert cooldowns, incident lifecycle, camera health checks) is what makes the thing usable, and it taught me more. Cameras die silently, and a dead camera watching a furnace is worse than no camera at all.

Repo and a demo clip in the comments. If you've done computer vision anywhere near safety-critical work, I'd genuinely like to hear how you handle the false positive problem.

#ComputerVision #MachineLearning #YOLO #Python #FireSafety

## Short variant (punchier, if you want a smaller post)

Fire detection AI is easy. Not crying wolf is the hard part.

I built PyroGuard to solve exactly that: a YOLO11n model watching camera streams, where no alert fires until 3 detections confirm within 5 seconds. Then it saves the evidence, logs the incident, and notifies you over email, Telegram, or webhook.

Honest numbers on the D-Fire test set: 0.77 precision, 0.69 recall. Not perfect, which is exactly why it ships in dry-run mode by default.

The plumbing around the model (incident lifecycle, alert cooldowns, camera health checks) taught me more than the training did.

Demo in the comments. How do you handle false positives in safety-adjacent CV?

#ComputerVision #MachineLearning #YOLO #FireSafety

## First comment (paste this immediately after posting)

Repo: <your GitHub link>
Demo clip: <attach or link a short clip>
Stack: Python, Ultralytics YOLO, FastAPI, SQLite. Cameras can be webcam, video file, or RTSP streams, each with its own health monitoring. Happy to walk through the temporal verification logic if anyone's curious.

## Visuals to attach (in priority order)

1. **Best: a 20-30s screen recording** of the live detection window with boxes drawn (`python scripts/test_camera.py --source test_video.mp4`, or capture the pyroguard ui). Native video beats every static image on reach, roughly tripling it.
2. **If no video:** `runs/detect/train/confusion_matrix_normalized.png` — fire detected correctly 84% of the time, smoke 73%, and of the false positives it does make, 63% are smoke. Posting your own confusion matrix (weaknesses visible) reads as confident, not weak. Most project posts only show glossy demo clips.
3. `runs/detect/train/results.png` — training curves over 50 epochs, good as a second image.
4. `val_batch0_pred.jpg` next to `val_batch0_labels.jpg` — a "what the model sees" side-by-side.

## Posting checklist

- GitHub link goes in the FIRST COMMENT, never the post body. LinkedIn's algorithm suppresses posts with external links in the body.
- The first two lines show before the "see more" fold. The hook is written to survive it, so don't add anything above it.
- Best window: Tuesday-Thursday, 8-10am in your audience's timezone.
- Reply to every comment in the first hour; early engagement is what pushes it into feeds beyond your network.
- 5 hashtags is the cap. Don't add more.
