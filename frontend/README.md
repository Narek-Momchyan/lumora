# Lumora frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4. All data comes
from the Django API (`../backend`) through native `fetch`.

```text
app/         routes: pages and layouts. `(site)/` holds every page behind the login, with the
             shared sidebar and header in its layout
components/  shared components, `auth/` the login page, `layout/` the sidebar and header,
             `lobby/` the lobby page, `zeus/` the Zeus Legacy game
lib/         `api.ts` for the browser (cookies, CSRF header, errors), `server-api.ts` for server components,
             `content.ts` for page content, `lang.ts` for the visitor's language, `zeus.ts` for bet steps,
             speeds and turning pays into LC
types/       TypeScript interfaces for the API responses (they mirror the backend serializers)
proxy.ts     sends visitors without a session to /login and renews an expired access token
```

## Run

The backend must be running first (see `../backend/README.md`).

```bash
npm install
copy .env.example .env.local
npm run dev
```

`.env.local` holds `BACKEND_URL=http://127.0.0.1:8000`, which is private to the
Next server, and the auth cookie names that `proxy.ts` reads. Use `127.0.0.1`, not `localhost` (Node.js may resolve `localhost` to
IPv6). `next.config.ts` rewrites `/api/*` and `/media/*` to Django, so open the site
at <http://localhost:3000> and the browser talks to Next. The one exception is the public
Neon Crash feed: the browser connects to Django at `NEXT_PUBLIC_WS_URL`, so restart
`npm run dev` after changing it.

Scripts: `npm run dev`, `npm run build`, `npm run start`, `npm run lint`.

## Design

Figma file "Lumora — Web Design": 01 Login, 02 Lobby, 03 Game · Neon Crash,
04 Wallet. The colours are Tailwind tokens in `app/globals.css`, so classes look
like `bg-bg`, `bg-surface`, `bg-surface2`, `border-border`, `text-text`,
`text-muted`, `text-cyan`, `text-magenta`, `text-lime`, `text-danger`.
Fonts: Sora for headings, Inter for text. Sora has no Armenian or Cyrillic letters and
Inter no Armenian ones, so `app/globals.css` picks the font by `<html lang>`: Russian
headings use Inter, and Armenian uses Noto Sans Armenian everywhere.

## Content and languages

No text or image is written in the code. Server components read the language with
`displayLang()` from `lib/lang.ts` (the `lang` cookie, else `en`) and load texts through
`lib/content.ts`, then pass them to client components as props. The texts come from the
backend, so run `python manage.py load_sample` there first. `LanguageSwitcher` sets the
`lang` cookie and calls `router.refresh()`. API errors already arrive in the chosen
language: show their `detail` and field messages as they are.

## Zeus Legacy

The page at `/zeus-legacy` only animates. `POST /api/slot_spins` returns the whole round,
and `components/zeus/useZeusRound.ts` plays its spins and tumbles step by step; nothing is
calculated or rolled in the browser. The player starts each free spin with the Spin button
(autoplay goes on by itself), although the backend has already settled them all. The balance
on the page changes to the `balance` of
that response when the round ends. Animations use `motion` (`motion/react`) with the same
settings as the original Zeus Legacy, and `app/(site)/zeus-legacy/zeus.css` holds its CSS
keyframes. Normal speed matches the original; `SPEEDS` in `lib/zeus.ts` makes turbo and
instant faster. The game's own colours are the `zeus-*` tokens in `app/globals.css`.

Sounds come from `/api/slot_sounds`, so run `python manage.py load_sounds` in the backend
first. They load after the first click or key press, because browsers refuse sound before
that. A sound with no file is silent, and the mute choice is the only thing kept in
`localStorage`.

## Notes for the API types

- Money fields are strings (`"10000.00"`), so they are `string` in interfaces.
- Times are ISO strings (`"2026-10-30T17:49:52.600009Z"`).
- Lists are arrays; `me` and `wallet` are single objects.
- In client components use `apiFetch` from `lib/api.ts`. It sends `X-CSRFToken`, and
  on a `401` it calls `POST /api/token/refresh` and retries once. If that fails it
  throws `ApiError`, so `error.status === 401` means "send to login".
- In server components use `serverFetch` from `lib/server-api.ts`, which forwards
  the visitor's cookies to Django. Call `await connection()` first when the page
  must not be prerendered.
- The JWTs live only in httpOnly cookies set by the backend: JavaScript never sees
  them, and nothing is kept in `localStorage`.
- Show "Demo mode · LC has no cash value" wherever a balance is shown.
