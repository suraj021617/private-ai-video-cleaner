# Frontend — Private AI Video Cleaner

Next.js (App Router) + TypeScript + Tailwind CSS.

## Scripts

```bash
npm install
cp .env.example .env.local
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

## Routes

| Path | Purpose |
|------|---------|
| `/` | Landing |
| `/bootstrap` | First owner setup |
| `/login` | Sign in |
| `/upload` | Secure video upload |
| `/library` | Video library |
| `/editor/[videoId]` | Selection editor |

## Editor (Phase 3)

Mobile-first CapCut/VN-style tools: preview, timeline, play/pause, seek, frame step, zoom, rectangle/brush selection, undo/redo, mask preview, save/load masks.

API calls are same-origin via Next rewrites (`BACKEND_URL`).
