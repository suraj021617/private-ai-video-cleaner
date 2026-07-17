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

## Structure

```
src/
  app/           # Routes & layouts
  components/    # UI (ui/, editor/, auth/ — filled in later phases)
  lib/           # Config & API helpers
  styles/        # Optional extra stylesheets
  types/         # Shared TS types
```

Phase 1 ships a branded dark shell and design tokens only.
