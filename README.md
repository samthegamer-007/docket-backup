# Docket

A legal dispute tracker for ordinary people, disguised as an Android app.

Most people don't fail at legal problems because they don't understand the law — they fail because they don't know what step 2 is, forget deadlines, and give up after one unanswered email. Docket treats a dispute as a **case with a timeline**, not a one-off question. It tracks where you are in the process, tells you what's next, and drafts the right document at each stage — all shown as a navigable node graph instead of a chat window.

**Not a chatbot. Not a legal-explainer. Not legal advice.** See `docs/architecture.md` for how we enforce that boundary structurally.

## Scope (v1)

- Rental deposit not returned
- E-commerce refund denied

## Repo Structure

```
docket/
├── backend/          Flask API — state machine, AI pipeline, case data
├── frontend/          Web UI — node-graph interface (this is the "web app" part)
├── mobile-wrapper/    Capacitor project that packages frontend/ into an installable APK
├── docs/              Architecture notes, timeline, glossary
└── README.md
```

## Why It's a "Web App Disguised as an Android APK"

The actual product is a web app (Flask backend + JS frontend). We use **Capacitor** to wrap the built frontend into a real installable `.apk` — so it looks, installs, and feels like a native Android app, but the logic underneath is the same web app either team member could run in a browser.

**Why Capacitor over a simple WebView-to-live-URL wrapper:** the contest restricts internet access during judging. Capacitor bundles the frontend files *inside* the APK itself, so the app opens and renders fine with no internet — only the actual AI/case-processing calls need a connection. A plain WebView pointing at a live hosted URL would break the moment there's no signal in the room.

## Getting Started

See setup instructions in each subfolder's README:
- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)
- [`mobile-wrapper/README.md`](mobile-wrapper/README.md)

## Team

- Samuel — backend / pipeline / frontend / UI
- Adreeto — backend / api 
- Sharbajit — [ To Be Decided ]
- Nilanjan — script, presentation, project report

## Docs

- [`docs/architecture.md`](docs/architecture.md) — full architecture, safety design, data sources
- [`docs/timeline.md`](docs/timeline.md) — day-by-day build timeline
- [`docs/glossary.md`](docs/glossary.md) — plain-language explanation of technical terms used throughout
