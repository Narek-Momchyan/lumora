# Lumora — notes for Claude Code

## Working with Narek

- Reply in Armenian, written in Armenian script. Code, comments, commit messages and
  docs stay in English.
- Before a bigger task, ask clarifying questions first (one at a time) instead of guessing.
- Claude Code writes the frontend one page at a time and Narek reviews every step.
  Before a page, show the plan (routes, files, components) and wait for his OK. After
  it, explain briefly what each new file does, so he understands and can defend the code.

## What Lumora is

A **football-first** gaming platform with **demo coins only**: demo bets on top football
leagues (odds from our own model), free score predictions with leaderboards, and club
forums. The casino games (Neon Crash, Zeus Legacy, Lumora Roulette) stay as a second
section, "Casino", at `/casino`. Every product decision for football is in
`design/sports-spec.md`; read it before any sports work.

Players get free Lumora Coins (LC). **LC has no cash value. There are no deposits,
withdrawals, payments or prizes, and we never add any.** It is a portfolio project for
iGaming backend / full-stack roles, so clean code, tests and clear maths matter more
than the number of features.

Languages: **en (default), am, ru**. The chosen language lives in the `lang` cookie,
like in Fruit Food (`am` is our code for Armenian; the HTML `lang` attribute is `hy`).

Design: Figma "Lumora — Web Design",
https://www.figma.com/design/FxLkT26ijHMkKgX87RjLyM. PNG exports are in `design/`
(open them before building a page): casino 01 Login, 02 Lobby, 03 Neon Crash,
04 Wallet, 05/05b/05c Roulette (betting, spin, result); football 06 Sports home,
07 Match, 08 My bets, 09 Predictions, 10 League table, 11 Club forum, 12 Forum topic.
The spec for 06–12 is `design/sports-spec.md`.

Two themes, one set of Tailwind class names: the colour tokens (`bg`, `surface`,
`surface2`, `border`, `text`, `muted`, `accent`, `accent2`, `lime`, `danger`) are CSS
variables in `frontend/app/globals.css`. The neon casino values sit on `:root`, the
green "night stadium" values under `[data-theme="sports"]` on `<html>`; keep both in
sync with Figma. Fonts: Sora for
headings, Inter for text. Build only what the API supports; if the design shows
something the backend does not have yet (forgot password, reset balance, live bets,
wagered stats), leave it out and list it for Narek instead of faking it.

## Stack

- `backend/` Django 6.1, Django REST Framework, SimpleJWT, django-cors-headers,
  python-decouple, PostgreSQL (installed on Windows, no Docker). Pipenv manages the
  environment in `backend/.venv`; `requirements.txt` is generated from `Pipfile.lock`.
- Live game: Django Channels with Redis (Memurai on Windows, 127.0.0.1:6379,
  `CHANNEL_REDIS_URL`); tests use `InMemoryChannelLayer`. Daphne serves ASGI.
- `frontend/` Next.js 16 (App Router, React Compiler), TypeScript, Tailwind CSS 4,
  native `fetch`.
- Later: `mobile/` React Native (Expo) on the same API.

## Commands (Windows)

```bash
# backend: always inside backend/
cd backend
pipenv install                             # everything from Pipfile.lock into backend/.venv
pipenv shell                               # every new terminal
pipenv install <package>                   # add a package, then:
pipenv requirements > requirements.txt
python manage.py migrate
python manage.py runserver                 # HTTP, the WebSocket and the rounds of both live games, needs Memurai
python manage.py run_crash                 # production only: Neon Crash's rounds as their own process
python manage.py run_roulette              # production only: Lumora Roulette's rounds as their own process
python manage.py test                      # all fast tests, ~2 min, needs PostgreSQL
python manage.py test --tag slow           # Zeus Legacy's 1,000,000-round RTP test, ~3 min
python manage.py makemigrations
# without the shell: pipenv run python manage.py test

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
- Run pipenv only inside `backend/`, never in the repo root, so it never creates a
  second Pipfile or virtualenv. `Pipfile`, `Pipfile.lock` and
  `requirements.txt` change together in one commit.
- Python uses double quotes (what Django 6 generates).
- Every endpoint is listed in the "Endpoints" table of `backend/README.md`; keep it
  up to date.

## Content, languages and errors (the same as in Fruit Food)

- **Every text and image on the site comes from the API and is edited in the Django
  admin**: labels, buttons, titles, the logo, game images. Nothing is hard-coded in
  the frontend.
- Each page has its own app, as in Fruit Food (`header`, `footer`, login labels in
  `accounts`, lobby labels and game translations in `games`, crash page labels in
  `crash`, wallet page labels in `wallet` ...). Models have a `lang` field
  (`base.constants.LANG_CHOICES`), endpoints are public, read-only and filtered with
  `?lang=`. Images are `FileField`s uploaded in the admin and returned as full URLs.
- `python manage.py load_sample` fills all content in en, am and ru, and the tests
  check that every collection has an endpoint (like Fruit Food's `ApiContractTests`).
- The patterns come from Narek's Fruit Food project
  (https://github.com/vsayyan/FruitFood, public; clone it outside `lumora/` to read it):
  `base/serializers.py`
  (`MediaFileField` returns full image URLs), `base/fields.py` (allowed image formats,
  5 MB limit), `base/admin.py` (`ImagePreviewMixin`), `LANG_CHOICES` in
  `base/constants.py`, a `load_sample` management command and an `ApiContractTests`
  class that compares every endpoint with the sample data.
- **Errors**: every API error has a `code`. Its text comes from the `ErrorMessage`
  model (code + lang, edited in the admin) in the request's language (`lang` cookie,
  default en); if a translation is missing, the English text is used.

## Auth

- JWT lives **only in httpOnly cookies** set by the backend (`/api/token`,
  `/api/register`, `/api/token/refresh`, `/api/logout`); never in localStorage or JS.
- The one exception is the public, cookie-free live feeds (`/ws/crash`, `/ws/roulette`):
  the browser connects to Django directly at `NEXT_PUBLIC_WS_URL` and
  `NEXT_PUBLIC_ROULETTE_WS_URL`.
- Everything else in the browser talks only to the Next app: `next.config.ts` rewrites `/api/*` and
  `/media/*` to Django, so the cookies are first-party and no CORS is needed. Unsafe
  requests send Django's CSRF token in the `X-CSRFToken` header.
- `frontend/proxy.ts` sends every page except `/login` to `/login` when there is no
  session cookie, before the page renders. Logged-in players who open `/login` go to `/`.
- `proxy.ts` also picks the section: football routes are `sports`, casino routes (and
  `/login`) are `casino`, shared pages (Wallet, Leaderboard) keep the last one. It saves
  it in the `mode` cookie, and the root layout sets `<html data-theme>` from it.

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
   Store `server_seed_hash`, `client_seed` and `nonce` on every bet. The live games
   (Neon Crash, Lumora Roulette) are the exception: their rounds are shared, so their seeds
   come from a hash chain (`fairness/chain.py`) and live on the round, not on the bet.
   Football is outside this rule: its results are real matches, not RNG.
5. **Game maths lives in a pure `engine.py`** (no Django, no database).
   `services.py` glues engine + wallet + fairness.
6. **Bet and settle in one database transaction.** If anything fails, nothing is
   charged and the nonce is not used. The live games have them apart by nature: each
   step is its own transaction that first locks the round's row (order: round, bet, wallet).
   Football: placing a bet locks the selection rows (by id) then the wallet; settling locks
   the bet then the wallet; pricing locks only selection rows.
7. **Every game ships with an RTP simulation test** (at least 200,000 rounds) that
   asserts its RTP. A test too slow for `python manage.py test` is tagged `slow` and
   runs with `python manage.py test --tag slow`; run it after changing that game's maths.
   Football: a 200,000-match simulation from the model shows that a bettor gets back
   1/(1 + margin) (`--tag slow`).
8. Endpoints need a JWT by default; public ones set `permission_classes = [AllowAny]`.
9. The admin never edits money or history: wallets, transactions, seed pairs and bets
   are read-only there.
10. Tests are Django `TestCase` classes in each app's `tests.py` (`SimpleTestCase` for
    pure engines, `TransactionTestCase` for real parallel requests).
    `python manage.py test` must pass before every commit. Create test users without
    a password (fast); only the `accounts` tests use real passwords.
11. Frontend: Tailwind tokens (`bg-surface`, `text-muted`, `text-accent` ...), never raw
    hex. Show "Demo mode · LC has no cash value" wherever a balance is shown.
12. No text or image is hard-coded in the frontend: it comes from the backend in the
    current language and can be changed in the admin.
13. Tokens only in httpOnly cookies. No page except `/login` opens without a session.
14. **Odds come only from our model** (`sports/engine.py`), never from a provider or a
    bookmaker, and are frozen at kickoff.
15. **Settlement uses only football-data.org's final score** (status FINISHED, regular
    time), in an idempotent job; postponed, cancelled or abandoned matches are void as in
    `design/sports-spec.md`.
16. **The frontend never calls a football provider.** Sync jobs store everything in our
    database and the browser reads only our API. Tests never use the network: they read
    recorded JSON fixtures.
17. Club crests come only from football-data.org's `crest` (saved in `Team.crest`,
    replaceable in the admin), with the club's initials in its colours as the fallback.
    We never use league logos: leagues show country flags (a star for the Champions League).
18. Components never check the theme: colours only through the tokens.

## Frontend conventions

- TypeScript strict, no `src/` folder; `@/*` points to the `frontend/` root.
- `lib/api.ts` is the fetcher: every request goes through it (same-origin `/api/...`,
  cookies, CSRF header, one refresh on 401, `ApiError`). Server components forward the
  request's cookies to Django. `types/` holds the interfaces that mirror the backend
  serializers.
- Native `fetch`, no axios.
- Shared UI lives in `components/ui/` (Card, Button primary/ghost/outline, Badge, Chip,
  Tabs, PageTitle, SectionTitle, Field, ProgressBar, OddsButton). Pages use these
  instead of repeating classes.
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
- [ ] Auth in httpOnly cookies, `/api/logout`, CSRF, Next rewrites + `proxy.ts` guard
- [ ] Languages en/am/ru, content apps with admin-edited texts and images,
      `ErrorMessage` with codes, `load_sample`
- [ ] Frontend (Claude Code writes, Narek reviews): Login / Sign up, Lobby, Neon Crash,
      Wallet, Leaderboard (Figma 01–04), language switcher

### Phase 2 — Live Neon Crash (multiplayer)
- [x] Round loop: betting window (7 s) → flight → crash → pause, run by `run_crash`
      (one runner at a time, PostgreSQL advisory lock)
- [x] Hash-chain seeds for shared rounds (each round's seed = SHA-256 of the next)
- [x] Django Channels + Redis: round state, bets and cash-outs over `/ws/crash`
      (no ticks: the multiplier is a formula of time, the frontend draws the same one)
- [x] Manual cash-out with server-side time checks, auto cash-out, row lock against the crash
- [x] Demo bots set in the admin, solo crash removed, `CrashPageLabel`
- [x] Live bets panel and round history in the UI (Figma 03)
- [ ] Load test with 200 simulated players

### Phase 3 — Lumora Roulette
- [x] Live table: betting (18 s) → spin (8 s) → settle (4 s pause), run by `run_roulette`
- [x] Hash-chain seeds, every bet of the table, exact RTP 36/37, slips with several lines
- [x] `/ws/roulette`, demo bots set in the admin, `RoulettePageLabel`
- [x] Frontend: wheel animation, chip selector, betting board, `is_playable` on

### Phase 4 — Zeus Legacy inside Lumora (`slots/`)
- [x] Port the spin engine from the Zeus_Legacy repo into `slots/engine.py` as pure
      functions (grid, cascades, multipliers, free spins) that take a float stream
- [x] Use `fairness.rng.float_stream(server_seed, client_seed, nonce)` instead of its RNG
- [x] Use `wallet.services.debit/credit` instead of its own balance code
- [x] 1,000,000-round RTP test (`--tag slow`; measured about 96.6%, bonus buy about 97.2%)
- [x] `POST /api/slot_spins`, jackpot pools, symbols, sounds and page texts in the admin
- [x] Frontend: the Zeus Legacy page, `is_playable` on
- [ ] Next step: Ante Bet (x1.25 stake, more scatters), as in the Zeus_Legacy repo

### Phase 5 — Polish and deploy
- [ ] Rate limiting on auth and bets
- [ ] "Verify a round" page (paste the seeds, recompute the result in the browser)
- [ ] Responsible-play touches: session timer, loss limits (even with demo coins)
- [ ] Deploy the frontend, the backend and PostgreSQL

### Phase 6 — Mobile (React Native / Expo)
- [ ] Shared API client, Lobby, Neon Crash, Wallet

### Football (design/sports-spec.md, one session per phase)
- [ ] S0 Theme tokens + Sports | Casino switch + both sidebars + shared UI kit
      (`components/ui/`) + casino pages consistent with designs 01–05
- [ ] S1 `sports` backend data: competitions, teams (colours, aliases, crests), matches,
      standings, football-data sync with rate limits, admin, tests on recorded JSON
- [ ] S2 Odds engine, markets, bets (single/express), settlement, void rules, tests and
      the 200,000-match simulation
- [ ] S3 Frontend: Football home, match page, bet slip, My bets (designs 06–08) +
      animations 1–4
- [ ] S4 Predictions and leaderboards (design 09), league pages (design 10)
- [ ] S5 Live scores (API-Football, budget guard) over `/ws/sports`, live page
- [ ] S6 Club forums with moderation (designs 11–12)
