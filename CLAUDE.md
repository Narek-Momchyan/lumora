# Lumora — notes for Claude Code

## Working with Narek

- Reply in Armenian, written in Armenian script. Code, comments, commit messages and
  docs stay in English.
- Before a bigger task, ask clarifying questions first (one at a time) instead of guessing.
- Narek writes the frontend himself. Don't generate frontend pages or components unless
  he asks for them; explain, review, or give small snippets.

## What Lumora is

A casino-style gaming platform with **demo coins only**. Players get free Lumora Coins
(LC). **LC has no cash value. There are no deposits, withdrawals, payments or prizes,
and we never add any.** It is a portfolio project for iGaming backend / full-stack
roles, so clean code, tests and clear maths matter more than the number of features.

Design: Figma "Lumora — Web Design",
https://www.figma.com/design/FxLkT26ijHMkKgX87RjLyM — screens 01 Login, 02 Lobby,
03 Game · Neon Crash, 04 Wallet. The colour variables ("Lumora Colors") are the
Tailwind tokens in `frontend/app/globals.css`; keep both in sync. Fonts: Sora + Inter.

## Stack

- `backend/` Django 6.1, Django REST Framework, SimpleJWT, django-cors-headers,
  python-decouple, PostgreSQL (installed on Windows, no Docker), Pipenv.
- `frontend/` Next.js 16 (App Router, React Compiler), TypeScript, Tailwind CSS 4,
  native `fetch`.
- Later: `mobile/` React Native (Expo) on the same API.

## Commands (Windows)

```bash
# backend
cd backend
pipenv install
pipenv shell
python manage.py migrate
python manage.py runserver
python manage.py test              # all tests, ~5 s, needs PostgreSQL
python manage.py makemigrations

# frontend
cd frontend
npm install
npm run dev
npm run lint
npx tsc --noEmit
npm run build
```

## Backend conventions (the same as in Fruit Food)

- The project package is `base/`; apps sit directly in `backend/` (no `apps/` folder).
- An app has `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`,
  `tests.py`, plus `services.py` when it changes data and `engine.py` for game maths.
- Views are DRF ViewSets. Collections extend `base.views.FilteredReadOnlyViewSet`
  (`filter_fields`, `list_limit`); one-object endpoints extend `SingleObjectViewSet`.
- Each app's `urls.py` has `<app>_router = DefaultRouter(trailing_slash=False)`;
  `base/urls.py` adds its registry to `OptionalSlashRouter`. A new app → import its
  router there and add the app to `INSTALLED_APPS`.
- URLs are `/api/<snake_case_collection>`, trailing slash optional. Lists are plain
  arrays without pagination. Filters are query parameters; an unknown value returns
  `[]` with 200.
- Money in JSON is a string with two decimals. Errors are `{"detail": "..."}`.
- Models have `class Meta` with `verbose_name_plural`, `ordering` and named
  constraints. Admin classes use `@admin.register` and lists for `list_display`,
  `list_filter`, `search_fields`.
- Settings come from `.env` through python-decouple. Never commit `.env`; every new
  setting goes into `.env.example` too.
- Python uses double quotes (what Django 6 generates).
- Every endpoint is listed in the "Endpoints" table of `backend/README.md`; keep it
  up to date.

## Rules — do not break these

1. **Demo coins only.** Never add deposits, withdrawals, payments, cash value, or any
   way to turn LC into money or prizes.
2. **Money moves only through `wallet/services.py`** (`open_wallet`, `debit`, `credit`,
   `claim_daily_bonus`). Never set `wallet.balance` anywhere else. Every change writes
   a `Transaction` in the same `transaction.atomic()` block with the wallet row locked
   by `select_for_update()`. The ledger is append-only.
3. **Decimal, never float, for money**, quantised to 0.01.
4. **Game results come only from `fairness/rng.py`**, with the player's active
   `SeedPair` and the nonce from `fairness.services.next_nonce`. Never use `random`.
   Store `server_seed_hash`, `client_seed` and `nonce` on every bet.
5. **Game maths lives in a pure `engine.py`** (no Django, no database).
   `services.py` glues engine + wallet + fairness.
6. **Bet and settle in one database transaction.** If anything fails, nothing is
   charged and the nonce is not used.
7. **Every game ships with an RTP simulation test** (at least 200,000 rounds) that
   asserts its RTP.
8. Endpoints need a JWT by default; public ones set `permission_classes = [AllowAny]`.
9. The admin never edits money or history: wallets, transactions, seed pairs and bets
   are read-only there.
10. Tests are Django `TestCase` classes in each app's `tests.py` (`SimpleTestCase` for
    pure engines, `TransactionTestCase` for real parallel requests).
    `python manage.py test` must pass before every commit. Create test users without
    a password (fast); only the `accounts` tests use real passwords.
11. Frontend: Tailwind tokens (`bg-surface`, `text-muted`, `text-cyan` ...), never raw
    hex. Show "Demo mode · LC has no cash value" wherever a balance is shown.

## Frontend conventions

- TypeScript strict, no `src/` folder; `@/*` points to the `frontend/` root.
- `lib/` holds the fetcher (base URL from `NEXT_PUBLIC_API_URL`, JWT header, errors);
  `types/` holds the interfaces that mirror the backend serializers.
- Native `fetch`, no axios.
- Style: no semicolons, single quotes in TS, double quotes in JSX attributes.
- Next.js 16 has breaking changes compared with older versions. When unsure about an
  API, read the guide in `frontend/node_modules/next/dist/docs/` first. `next dev`
  writes `frontend/AGENTS.md` with this hint; it is git-ignored.

## Roadmap

Each phase ends with something that works and can be shown.

### Phase 1 — Foundation
- [x] Backend: email + JWT auth, signup grant of 10,000 LC
- [x] Wallet + append-only ledger, atomic debit/credit with row locks, idempotency keys
- [x] Daily bonus of 5,000 LC (24-hour cooldown)
- [x] Provably fair RNG (server seed hash, client seed, nonce) + seed rotation
- [x] Game catalogue, Neon Crash (solo, auto cash-out, RTP 97% by simulation)
- [x] European roulette maths (exact RTP 36/37), weekly leaderboard
- [x] Tests on PostgreSQL, including parallel bets
- [ ] Frontend (Narek): Login / Sign up, Lobby, Neon Crash, Wallet, Leaderboard (Figma 01–04)

### Phase 2 — Live Neon Crash (multiplayer)
- [ ] Round loop: betting window (7 s) → flight → crash, run by a background task
- [ ] Hash-chain seeds for shared rounds (each round's seed = SHA-256 of the next)
- [ ] Django Channels + Redis: broadcast ticks, bets and cash-outs over WebSocket
- [ ] Manual cash-out with server-side time checks
- [ ] Live bets panel and round history in the UI (Figma 03)
- [ ] Load test with 200 simulated players

### Phase 3 — Lumora Roulette
- [ ] API + wallet wiring for `roulette/engine.py` (several bets per spin)
- [ ] Wheel animation, chip selector, betting board

### Phase 4 — Zeus Legacy inside Lumora (`slots/`)
- [ ] Port the spin engine from the Zeus_Legacy repo into `slots/engine.py` as pure
      functions (grid, cascades, multipliers, free spins) that take a float stream
- [ ] Use `fairness.rng.float_stream(server_seed, client_seed, nonce)` instead of its RNG
- [ ] Use `wallet.services.debit/credit` instead of its own balance code
- [ ] 1,000,000-spin RTP test (target 96.5%)

### Phase 5 — Polish and deploy
- [ ] Refresh token in an httpOnly cookie, rate limiting on auth and bets
- [ ] "Verify a round" page (paste the seeds, recompute the result in the browser)
- [ ] Responsible-play touches: session timer, loss limits (even with demo coins)
- [ ] Deploy the frontend, the backend and PostgreSQL

### Phase 6 — Mobile (React Native / Expo)
- [ ] Shared API client, Lobby, Neon Crash, Wallet

### Phase 7 — Sports (demo predictions)
- [ ] Match data from a public sports API, pick the winner with demo coins
