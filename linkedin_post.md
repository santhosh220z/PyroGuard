# LinkedIn post for PyroGuard (v3 — rewritten with social-media-posts + bytesagain-social-copywriter + humanizer)

## Main post (copy-paste ready, plain text — LinkedIn doesn't render markdown)

The hardest part of building a fire detection AI wasn't detecting fire. It was teaching it not to cry wolf.

I've spent the past few weeks building PyroGuard: a YOLO11n model I trained on the D-Fire dataset, watching camera streams and deciding what's actually worth waking someone up for.

Detecting fire was the easy part. Any decent model draws boxes on flames. The hard part is everything that looks like fire but isn't: smoke, steam, haze in a bright lens. On my test set, 63% of the false positives were smoke. And one false alarm at 3am is how a monitoring system loses everyone's trust.

That's why the pipeline never trusts a single frame:

→ YOLO flags fire or smoke candidates on every frame
→ Nothing gets confirmed until 3 detections land within a 5 second window
→ Only then: evidence snapshot saved, incident written to SQLite, alert fired through email, Telegram, or a webhook
→ Alerts have cooldown, deduplication, and a circuit breaker, because notification services fail in creative ways

Every incident carries a full lifecycle: detected, confirmed, alert sent, acknowledged, resolved. Or marked as a false positive, which matters just as much.

Honest numbers: 0.77 precision, 0.69 recall, 0.77 mAP50. A nano model gets you surprisingly far, but it's nowhere near certified-safety grade, and I'm not pretending otherwise. That's also why it ships in dry-run mode by default: until you flip the switch, it logs what it would have alerted instead of actually alerting.

The model was the fun part. The plumbing around it (alert cooldowns, incident lifecycle, camera health checks) is what makes it usable, and it taught me more. Cameras die silently, and a dead camera watching a furnace is worse than no camera at all.

Repo and a demo clip in the comments. If you've done computer vision anywhere near safety-critical work, I'd genuinely like to hear how you handle the false positive problem.

#ComputerVision #MachineLearning #YOLO #Python #FireSafety

## Hook A/B testing kit

Five alternate opening hooks, same body. Adapted from the copywriter's five patterns (question / statement / data / story / contrarian) and grounded in PyroGuard's real numbers — no invented stats.

A — Question hook:
"What do a bonfire, a steam vent, and a hazy sunset have in common? To my fire detection model, all three can look like fire."

B — Statement hook:
"The naive version of fire detection alerts on everything. The fix wasn't a bigger model. It was making it wait."

C — Data hook (strongest, uses your real confusion matrix):
"63% of my fire detection model's false positives are smoke. That number is why no alert fires on a single frame."

D — Story hook:
"One false alarm at 3am is all it takes for people to stop trusting a monitoring system. So I built mine to earn every alert."

E — Contrarian hook:
"Unpopular opinion: the model is the least interesting part of a fire detection AI."

Test guide (from the copywriter, adapted):
- Post two variants 48 hours apart, same time of day.
- Measure engagement rate (comments + shares = distribution), not just likes.
- Whichever hook you pick, nothing goes above it. The first two lines are what survive the "see more" fold.
- Run ~5 posts per variant before declaring a winner.

## Short variant (punchier, for a re-post or a smaller first post)

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

## Hashtags (copywriter strategy, merged)

The copywriter's LinkedIn rule: 3-5 hashtags, placed at the end of the post, never inline. Its suggested tags (#Leadership #ProfessionalDevelopment #CareerGrowth) are generic job-seeker tags — for a practitioner project post, the 5 domain tags in the main post (#ComputerVision #MachineLearning #YOLO #Python #FireSafety) reach the right audience. Keep those; the tiered mega/niche mix from the copywriter applies to Instagram, not here.

## Visuals to attach (in priority order)

1. **Best: a 20-30s screen recording** of the live detection window with boxes drawn (`python scripts/test_camera.py --source test_video.mp4`, or capture the pyroguard ui). Native video beats every static image on reach, roughly tripling it.
2. **If no video:** `runs/detect/train/confusion_matrix_normalized.png` — fire detected correctly 84% of the time, smoke 73%, and of the false positives it does make, 63% are smoke. This image also backs up the Data hook (variant C) if you use it. Posting your own confusion matrix (weaknesses visible) reads as confident, not weak.
3. `runs/detect/train/results.png` — training curves over 50 epochs, good as a second image.
4. `val_batch0_pred.jpg` next to `val_batch0_labels.jpg` — a "what the model sees" side-by-side.

## Posting checklist

- GitHub link goes in the FIRST COMMENT, never the post body. LinkedIn's algorithm suppresses posts with external links in the body.
- The first two lines show before the "see more" fold. Don't add anything above the hook.
- Best window: Tuesday-Thursday, 8-10am in your audience's timezone.
- Reply to every comment in the first hour; early engagement is what pushes it into feeds beyond your network.
- 5 hashtags is the cap.
