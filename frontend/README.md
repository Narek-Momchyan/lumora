# Lumora frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4. All data comes
from the Django API (`../backend`) through native `fetch`.

```text
app/      routes: pages and layouts
lib/      the API fetcher: base URL from NEXT_PUBLIC_API_URL, JWT header, errors
types/    TypeScript interfaces for the API responses (they mirror the backend serializers)
```

## Run

The backend must be running first (see `../backend/README.md`).

```bash
npm install
copy .env.example .env.local
npm run dev
```

`.env.local` holds `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api`. Use
`127.0.0.1`, not `localhost` (Node.js may resolve `localhost` to IPv6).

Scripts: `npm run dev`, `npm run build`, `npm run start`, `npm run lint`.

## Design

Figma file "Lumora — Web Design": 01 Login, 02 Lobby, 03 Game · Neon Crash,
04 Wallet. The colours are Tailwind tokens in `app/globals.css`, so classes look
like `bg-bg`, `bg-surface`, `bg-surface2`, `border-border`, `text-text`,
`text-muted`, `text-cyan`, `text-magenta`, `text-lime`, `text-danger`.
Fonts: Sora for headings, Inter for text.

## Notes for the API types

- Money fields are strings (`"10000.00"`), so they are `string` in interfaces.
- Times are ISO strings (`"2026-10-30T17:49:52.600009Z"`).
- Lists are arrays; `me` and `wallet` are single objects.
- A `401` means the access token expired: get a new one from
  `POST /api/token/refresh` with the refresh token.
- Show "Demo mode · LC has no cash value" wherever a balance is shown.
