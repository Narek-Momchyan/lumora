# Lumora backend

Django + Django REST Framework API for Lumora, a casino-style gaming platform that
uses only demo coins (Lumora Coins, LC). LC has no cash value: there are no
deposits, withdrawals or real-money features.

## Requirements

- Python 3.12 or newer
- Pipenv (`pip install pipenv`)
- PostgreSQL 16 or newer
- Redis on port 6379 for the live Neon Crash feed. On Windows that is
  [Memurai](https://www.memurai.com/), which runs as a Windows service.

## Create the database (once)

Open **SQL Shell (psql)** from the Start menu (it comes with the PostgreSQL
installer), press Enter for the defaults and log in as `postgres` with the
password you chose when you installed PostgreSQL. Then run:

```sql
CREATE USER lumora WITH PASSWORD 'choose-a-password' CREATEDB;
CREATE DATABASE lumora OWNER lumora;
```

Put the same password in `.env` as `DB_PASSWORD`. `CREATEDB` lets
`python manage.py test` create and drop its temporary test database.

## Setup

```bash
cd backend
pipenv install                # creates backend/.venv from Pipfile.lock
copy .env.example .env        # then set SECRET_KEY and DB_PASSWORD
pipenv shell
python manage.py migrate
python manage.py load_sample
python manage.py createsuperuser
python manage.py runserver
```

- API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/
- Live feeds: ws://127.0.0.1:8000/ws/crash and ws://127.0.0.1:8000/ws/roulette

## Running Neon Crash

Rounds run only while their runner runs. In development `runserver` does that too, so
two things must be up:

1. **Memurai**: the Windows service starts with Windows. To check it, run
   `Get-Service Memurai` in PowerShell. Its address is `CHANNEL_REDIS_URL` in `.env`.
2. **The server**: `python manage.py runserver`. With `daphne` in `INSTALLED_APPS` it
   serves HTTP and the WebSocket, and `base/management/commands/runserver.py` also runs
   the rounds of Neon Crash and Lumora Roulette in two threads of its own.

Production has no `runserver`: there each game runs as its own process,
`python manage.py run_crash` and `python manage.py run_roulette`.

Only one runner of a game works at a time, because it holds a PostgreSQL advisory lock,
which is freed as soon as its process ends. A second `run_crash` refuses to start, and
the threads of `runserver` wait for the lock. A restarted runner continues the round it
finds in the database.

Without a runner there are no new rounds, and bets answer `round_closed`. Without
Redis the REST API and the money keep working, but the WebSocket stays quiet.

Run `pipenv shell` in every new terminal (in Git Bash use `cp` instead of
`copy`). The environment lives in `backend/.venv`; to keep it there, set the
environment variable `PIPENV_VENV_IN_PROJECT=1`. `migrate` also adds the game
catalogue (migration `games/0002_seed_games`).

## Football data

football-data.org's free plan (checked on its site, November 2026): our six
competitions (PL, PD, SA, BL1, FL1, CL), **10 requests a minute**, scores and schedules
**delayed** (no number given). Get a token at
https://www.football-data.org/client/register and put it in `.env` as
`FOOTBALL_DATA_TOKEN`; without it the rest of the site works and these commands refuse
to start.

```bash
python manage.py sync_football --full                  # the whole season: teams, crests, matches, tables
python manage.py sync_football                         # yesterday to tomorrow, and the tables
python manage.py sync_football --competition PL --full
python manage.py run_sports                            # keeps it fresh: one full sync a day after 03:00 UTC,
                                                       # today's matches every SPORTS_SYNC_INTERVAL_MINUTES on match days
```

- The browser never calls a provider: everything goes through our tables and API.
- `sports/providers/football_data.py` is the adapter: it waits in a 10-a-minute rate
  limiter, and on `429` it waits `X-RequestCounter-Reset` seconds and retries. Statuses
  map to ours in `STATUSES`. Bets will be settled on the regular-time score
  (`home_regular`, `away_regular`): the full-time score for a `REGULAR` match, else
  `regularTime`, else full time minus extra time.
- Every row is found by the provider's id, so a sync can run any number of times. Each
  competition's run is a `SyncRun` in the admin (requests, created, updated, errors).
- Crests are downloaded once per URL. An SVG crest is cleaned first (`base/svg.py`:
  only shapes, paints and gradients stay); a crest uploaded in the admin is never
  replaced (`crest_locked`). Badge colours start from `clubColors` and can be changed.
- Club and competition names come from the provider in English; `TeamName` and
  `CompetitionName` in the admin give the am/ru names, English is the fallback.
- `run_sports` is not started by `runserver` (unlike the live games), so a dev server
  never spends the request budget. One runner at a time (PostgreSQL advisory lock).

## Packages

- Add a package: `pipenv install <package>`, then update
  `requirements.txt`: `pipenv requirements > requirements.txt`.
- Without Pipenv (for example on a server): `pip install -r requirements.txt`.
- Commit `Pipfile`, `Pipfile.lock` and `requirements.txt` together.

## Connecting the frontend

The browser talks only to the Next app, which rewrites `/api/*` and `/media/*` to
Django. In `frontend/.env.local` (copied from `frontend/.env.example`):

```
BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000/ws/crash
NEXT_PUBLIC_ROULETTE_WS_URL=ws://127.0.0.1:8000/ws/roulette
```

The WebSockets are the one exception: they are public and need no cookies, so the browser
connects to Django directly. Two servers on one Redis share the feed, so a second
server for testing needs its own `CHANNEL_REDIS_URL`, for example `.../1`. Use `127.0.0.1`, not `localhost`: Node.js may resolve `localhost` to IPv6
(`::1`), while `runserver` listens on IPv4 only.

## API rules

- `/api/<name>`, with or without a trailing slash.
- Lists are plain JSON arrays without pagination. Feeds return only the newest
  rows: `transactions` the last 100; `crash_bets`, `crash_rounds`, `roulette_bets`,
  `roulette_rounds` and `seeds` the last 50.
- `me` and `wallet` return a single object.
- Filters are query parameters: `games` (`slug`, `category`), `transactions`
  (`kind`, `game`). An unknown value returns `[]` with status 200, not 404.
- Money is a string with two decimals (`"10000.00"`), never a number. Times are
  ISO 8601 in UTC.
- Errors always have a `code` and a `detail` in the request's language, see
  [Errors](#errors).
- The language comes from `?lang=`, then the `lang` cookie, then English. Supported:
  `en` (default), `am`, `ru`.
- Images are full URLs that start with `PUBLIC_BASE_URL`, so they load through the
  Next `/media` rewrite.
- Every endpoint needs a login except `register`, `token`, `token/refresh`,
  `logout`, `games`, `leaderboard`, `error_messages` and the site content: `logos`,
  `languages`, `sidebar_items`, `header_labels`, `sports_page_labels`, `login_page_labels`,
  `lobby_page_labels`, `game_categories`, `slot_symbols`, `slot_symbol_names`,
  `slot_sounds`, `jackpot_pools`, `zeus_page_labels`, `crash_rounds`,
  `crash_page_labels`, `roulette_rounds` and `roulette_page_labels`, and the football
  data: `competitions`, `teams`, `matches` and `standings`.
- The JWTs live only in httpOnly cookies, never in a response body and never in an
  `Authorization` header. `register` and `token` set `lumora_access` (30 minutes)
  and `lumora_refresh` (7 days), both `SameSite=Lax`, and `Secure` when
  `DEBUG=False`. A missing, expired or bad access cookie counts as not logged in:
  private endpoints answer `401`, public ones still work.
- CSRF: `register` and `token` also set Django's `csrftoken` cookie, which JavaScript
  can read. Every `POST`, `PUT`, `PATCH` and `DELETE` from a logged-in player, plus
  `token/refresh` and `logout`, must send its value in the `X-CSRFToken` header,
  otherwise the answer is `403`. `register` and `token` need no header. The browser's
  origin must be in `CSRF_TRUSTED_ORIGINS`.
- After a `401`, call `POST /api/token/refresh` once and repeat the request. A `401`
  from `token/refresh` means the session is over: it clears the cookies, so log in
  again.
- `logout` only deletes the cookies: the refresh token itself stays valid until it
  expires.

## Endpoints

| Method | URL | Login | What it does |
| --- | --- | --- | --- |
| POST | `/api/register` | – | `{email, password, display_name?}` → `201`, new player (same as `/api/me`) and a wallet with 10,000 LC; sets the auth and CSRF cookies |
| POST | `/api/token` | – | `{email, password}` → the player (same as `/api/me`); sets the auth and CSRF cookies |
| POST | `/api/token/refresh` | – | reads the refresh cookie → `204`, new access cookie; needs `X-CSRFToken` |
| POST | `/api/logout` | – | `204`, deletes the auth cookies; needs `X-CSRFToken` |
| GET | `/api/me` | cookie | the logged-in player |
| GET | `/api/wallet` | cookie | `{balance, last_bonus_at, bonus_available_at, updated_at}` |
| GET | `/api/transactions` | cookie | the player's ledger, newest first |
| POST | `/api/bonus` | cookie | daily bonus of 5,000 LC; `409` with `available_at` if claimed in the last 24 hours |
| GET | `/api/games` | – | active games, with `image` and `is_playable`; a game that isn't playable is coming soon |
| GET | `/api/crash_bets` | cookie | the player's Neon Crash bets, newest first |
| POST | `/api/crash_bets` | cookie | `{amount, target?}` → `201`, a bet on the open round with `balance`; `target` is the auto cash-out |
| POST | `/api/crash_bets/cash_out` | cookie | cashes out the player's bet at the server's multiplier → the bet with `balance` |
| GET | `/api/crash_rounds` | – | the last 50 crashed rounds with `seed`, `seed_hash`, `position` and `commitment` |
| GET | `/api/crash_rounds/<number>` | – | one crashed round; `404` until it has crashed |
| GET | `/api/crash_page_labels` | – | every text of the Neon Crash page; `?lang=` |
| GET | `/api/roulette_bets` | cookie | the player's last 50 slips with their lines and `seat` |
| POST | `/api/roulette_bets` | cookie | `{key, lines: [{bet_type, value?, amount}]}` → `201`, a slip on the open round with `balance`; a repeated `key` → `200`, the same slip |
| GET | `/api/roulette_bets/last_round` | cookie | `{round, lines}` of the player's last settled round, for Rebet |
| GET | `/api/roulette_rounds` | – | the last 50 settled rounds with `result`, `color`, `seed`, `seed_hash`, `position` and `commitment` |
| GET | `/api/roulette_rounds/<number>` | – | one settled round; `404` until it is settled |
| GET | `/api/roulette_page_labels` | – | every text of the roulette page and the names of the bets; `?lang=` |
| GET | `/api/seeds` | cookie | the player's provably fair seed pairs, the active one first |
| POST | `/api/seeds` | cookie | `{client_seed?}` → reveals the active server seed and starts a new pair: `{revealed, active}` |
| GET | `/api/leaderboard` | – | top 20 of the last 7 days by net game result |
| GET | `/api/logos` | – | the logo as one object, `{}` before one is added |
| GET | `/api/languages` | – | languages for the language switcher, in `order` |
| GET | `/api/sidebar_items` | – | the navigation of both sections: `mode` (`sports`/`casino`), `group` (`leagues`, `my` or none), `icon`, `order`, `is_soon` and `category` (a casino item with a category opens `/casino?category=<code>` and is active on that category's game pages); `?lang=` |
| GET | `/api/header_labels` | – | every text of the sidebar (with the Sports / Casino switch and the group headings) and the header; `?lang=` |
| GET | `/api/sports_page_labels` | – | every text of the football home page; `?lang=` |
| GET | `/api/competitions` | – | our active leagues with the flag and the current season (`current_matchday`); names in `?lang=` |
| GET | `/api/teams` | – | clubs with `tla`, badge colours and crest; `?competition=PL`; names in `?lang=` (English fallback) |
| GET | `/api/matches` | – | matches with both teams, status and every score (full, half, regular time, extra time, penalties); `?competition=`, `?date=YYYY-MM-DD` (UTC day), `?status=`, `?team=<id>`; at most 300 |
| GET | `/api/standings` | – | the current season's tables; `?competition=` |
| GET | `/api/login_page_labels` | – | every text of the login page; `?lang=` |
| GET | `/api/lobby_page_labels` | – | every text of the lobby page; `?lang=` |
| GET | `/api/game_categories` | – | category names: the filtered lobby's title and game cards; `?lang=` |
| GET | `/api/slot_spins` | cookie | the player's last 50 slot rounds, newest first, without `result` |
| POST | `/api/slot_spins` | cookie | `{game, amount, bonus_buy?}` → plays one round with all its free spins: the round, `result`, `balance` and `jackpot_pools` |
| GET | `/api/slot_spins/<id>` | cookie | one round with its `result` |
| GET | `/api/slot_symbols` | – | slot symbols with their images |
| GET | `/api/slot_symbol_names` | – | symbol names; `?lang=` |
| GET | `/api/slot_sounds` | – | active sounds that have an uploaded file |
| GET | `/api/jackpot_pools` | – | the current amount of each jackpot tier |
| GET | `/api/zeus_page_labels` | – | every text of the Zeus Legacy page; `?lang=` |
| GET | `/api/error_messages` | – | error texts; `?lang=`, `?code=` |
| WS | `/ws/crash` | – | the live round, read-only, see [Neon Crash](#neon-crash) |
| WS | `/ws/roulette` | – | the live table, read-only, see [Lumora Roulette](#lumora-roulette) |

`bonus_available_at` is `null` before the first bonus; a time in the past means
the bonus can be claimed now.

## Content and languages

Site texts and images are edited in the admin and read from the API, never written
in the frontend. Content models have a `lang` field (`base.constants.LANG_CHOICES`);
collections extend `base.views.LangFilteredViewSet`. An unknown `?lang=` returns `[]`
with 200, like any filter; an unknown `lang` cookie means English.

```bash
python manage.py load_sample            # adds only the missing rows
python manage.py load_sample --reset    # replaces the content with the sample
```

Fills every collection of `base.sample.COLLECTIONS` from `base/sample_db.json` in en,
am and ru (`--path` loads another file). By default it **only adds the rows that are
missing**, matched by each collection's natural key in `base.sample.NATURAL_KEYS`
(`lang`, `lang + code`, `lang + mode + url` ...), so texts edited in the admin stay.
`--reset` deletes those tables and loads the sample again, ids included; edits made in
the admin are lost. It never touches players, wallets, bets or games. To add a
collection: add the model, its endpoint, a key in `sample_db.json`, a row in
`base.sample.COLLECTIONS` and its natural key in `base.sample.NATURAL_KEYS`.

Images are plain `FileField`s with `base.fields.IMAGE_VALIDATORS`: JPG, PNG, WEBP or
GIF, 5 MB at most, and the file's first bytes must match a real image. SVG only where
a field uses `IMAGE_OR_SVG_VALIDATORS` (sidebar icons, crests, flags), and only an SVG
that `base/svg.py` finds already clean: `/media/` is served from the site's own origin
and an SVG can carry scripts. Media is served with
`Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox`
(`base/media.py`); the web server must send the same header in production. Files live in `media/`; `runserver` serves them only with `DEBUG=True`.

## Errors

Every error has a `code` and a `detail`, plus extras like `available_at`:

```json
{"code": "not_enough_lc", "detail": "Not enough LC."}
```

A bad field keeps its messages under the field name, with their codes in `field_codes`:

```json
{
  "code": "validation_error",
  "detail": "Check the fields.",
  "email": ["A player with this email already exists."],
  "field_codes": {"email": ["email_taken"]}
}
```

The text comes from `ErrorMessage` (code + lang, edited in the admin) in the request's
language. If that translation is missing the English text is used, and if there is
no row at all, the text written in the code. Texts may use placeholders, such as
`{min}` and `{max}` in `bet_out_of_range`. `errors/codes.py` lists every code, and a
test checks that each one has a text in every language. In our code, raise
`errors.exceptions.CodedError(code, text, **params)`.

## Provably fair

Every result comes from `HMAC_SHA256(server_seed, "client_seed:nonce:cursor")`.
Before playing, the player sees only `server_seed_hash`. Each bet uses the next
nonce (0, 1, 2 ...) and stores the hash, client seed and nonce. After
`POST /api/seeds` the old `server_seed` is revealed. A revealed pair was used for
nonces `0` to `nonce - 1`.

A slot round uses one nonce for everything, free spins included. To check one:

```python
stream = float_stream(server_seed, client_seed, nonce)
tier = slots.engine.roll_jackpot(cost, next(stream))
result = slots.engine.play_round(stream, bonus_buy=bonus_buy)
```

`result` equals the saved one, and `tier` equals `jackpot_tier`. The seeds prove only the
jackpot **tier**, not its amount: a pool is shared by all players and grows with their
stakes, so the amount that was paid is saved in `jackpot_win`.

### Verifying a Neon Crash round

A Neon Crash round is shared by everyone, so it can't use one player's seeds. It uses a
**hash chain** instead: every round's seed is the SHA-256 of the next round's seed. The
server makes the chain backwards from a secret last seed, then plays it forwards, so
a revealed seed says nothing about the next one.

Before the bets, every client gets `seed_hash`, the SHA-256 of the round's secret seed.
After the crash the `seed` is revealed. Take a round from `/api/crash_rounds` and check:

1. `sha256(seed) == seed_hash`: this is the seed promised before the bets.
2. `sha256(seed)` equals the `seed` of the round before, so the promise was already
   public. Hashing `seed` `position + 1` times gives `commitment`, the hash of the
   chain's first seed, so the whole chain was fixed when it was made.
3. The crash point comes out the same when you compute it again:

```python
import hashlib, hmac
from decimal import Decimal, ROUND_FLOOR

digest = hmac.new(seed.encode(), b"neon-crash:0:0", hashlib.sha256).digest()
r = (int.from_bytes(digest[:8], "big") >> 12) / 2**52
point = (Decimal("97") / (1 - Decimal(r))).to_integral_value(rounding=ROUND_FLOOR) / 100
point = min(max(point, Decimal("1")), Decimal("1000000"))
```

In this repo that is `crash.services.round_result(seed)`. Hashes are of the seed's
64-character hex text, not of its bytes.

The seeds prove that a result was fixed before the bets and that it wasn't changed for
anyone. They can't prove how the server chose the chain: it could have thrown away
chains it disliked, because no outside randomness goes in. For a demo-coin project
that is fine, and it is the honest limit of this design.

### Verifying a roulette round

Lumora Roulette uses the same kind of chain. Take a round from `/api/roulette_rounds`:
steps 1 and 2 above are the same, and the result is

```python
digest = hmac.new(seed.encode(), b"lumora-roulette:0:0", hashlib.sha256).digest()
r = (int.from_bytes(digest[:8], "big") >> 12) / 2**52
result = int(r * 37)
```

In this repo that is `roulette.services.round_result(seed)`.

## Neon Crash

One shared round at a time. `crash/engine.py` holds the maths and `crash/runner.py` is
the only code that moves a round:

1. `betting`: 7 seconds. `POST /api/crash_bets`, one bet per round.
2. `flying`: the multiplier grows from 1.00x, `POST /api/crash_bets/cash_out`.
3. `crashed`: the flight reached the crash point. Unpaid bets are lost and the seed is revealed.
4. A pause of 3 seconds, then the next round.

The multiplier is a formula of the time since `started_at`, in milliseconds:

```
multiplier = floor(100 * e^(0.00006 * ms)) / 100
```

So 2x comes after about 11.6 s and 10x after about 38 s. The frontend draws with the same
formula, so nothing is sent per tick. It should work out its clock offset from
`server_time`, which every round event carries.

**Cash-out.** The server computes the multiplier from its own clock. If that has reached
the crash point the answer is `too_late`, even when the round has not ended yet. A bet
with a `target` pays exactly `amount * target` when the flight reaches it, even if a
manual cash-out arrives later. A target equal to the crash point wins; a manual cash-out
at that moment is too late, so manual play can reach at most 0.01x below it.

**The race.** `place_bet`, `cash_out`, `pay_auto_cash_outs` and `crash_round` all start by
locking the round's row, always in the order round, bet, wallet. So a cash-out and the
crash run one after the other, and the second sees what the first did. Debits and
credits carry the idempotency keys `crash:<round>:bet` and `crash:<round>:win`.

The crash point is at most 1,000,000x, the highest target, which changes no player's RTP.

| Error | Status | When |
| --- | --- | --- |
| `round_closed` | 409 | a bet outside the betting window |
| `already_bet` | 409 | a second bet on the round |
| `not_flying` | 409 | a cash-out during betting |
| `too_late` | 409 | a cash-out at or after the crash point |
| `no_bet` | 409 | a cash-out without a bet on the round |
| `already_cashed_out` | 409 | a second cash-out |

### WebSocket

`/ws/crash` needs no login and is read-only: whatever a client sends is ignored. The
`Origin` header must be one of `CSRF_TRUSTED_ORIGINS`. A new client first gets a snapshot,
then every event. All of them are JSON with a `type`.

| `type` | Fields |
| --- | --- |
| `snapshot` | `round` (`null` before the first one), `history` (the last 20 as `{number, crash_point}`, newest first), `bets`, `server_time` |
| `round.betting`, `round.flying`, `round.crashed` | `number`, `status`, `seed_hash`, `betting_ends_at`, `started_at`, `server_time`; after the crash also `crash_point`, `seed`, `crashed_at` |
| `bet.placed`, `bet.cashed_out` | `id`, `round`, `player`, `amount`, `multiplier`, `payout`, `is_bot` |

`round` in a snapshot has the fields of a round event, and `bets` those of `bet.placed`.
`multiplier` is `null` until the bet is cashed out. A live round's `seed` and `crash_point`
are never sent, and only `crash/feed.py` decides what the feed shows.

### Demo bots

The bots keep the feed alive: admin → Crash bot settings sets on/off, how many bet in a
round (at most one per name), their bet range and their names. They live in `CrashBotBet`
with no user, so they can't reach a wallet, the ledger or the leaderboard, and they are
marked `is_bot`. A bot's target is drawn before the flight, so it knows nothing about
the crash point. Only the current round's rows are kept. `load_sample` doesn't touch them.

## Lumora Roulette

European roulette (one zero) at one table shared by everyone. `roulette/engine.py` holds
the maths and `roulette/runner.py` is the only code that moves a round:

1. `betting`: 18 seconds. `POST /api/roulette_bets`, as many slips as you like.
2. `spinning`: 8 seconds. No more bets. `result` goes out, so that the wheel stops on it.
3. `settled`: every winning slip gets one credit and the seed is revealed.
4. A pause of 4 seconds, then the next round.

A bet is a set of covered pockets and pays `36 / pockets` times the stake, so every bet
has the exact RTP of 36/37 = 97.30%. `engine.resolve_bet` is the one place that knows
which bets the table has, and `split` 8/11 is fine while 8/12 is `invalid_bet`.

| `bet_type` | `value` | Pays, with the stake |
| --- | --- | --- |
| `straight` | `[17]` | 36 |
| `split` | `[8, 11]`, also `[0, 1]` to `[0, 3]` | 18 |
| `street` | `[7, 8, 9]` | 12 |
| `trio` | `[0, 1, 2]`, `[0, 2, 3]` | 12 |
| `corner` | `[20, 21, 23, 24]` | 9 |
| `first_four` | `[0, 1, 2, 3]` | 9 |
| `six_line` | `[1, 2, 3, 4, 5, 6]` | 6 |
| `dozen` | `[1]`, `[2]`, `[3]` | 3 |
| `column` | `[1]`, `[2]`, `[3]` | 3 |
| `red`, `black`, `even`, `odd`, `low`, `high` | none | 2 |

**Slips.** One POST is one slip, with one debit for all its lines. `key` is made by the
client (`crypto.randomUUID()`) and can be up to 36 characters: the same key finds the same
slip, in any round, and charges nothing. A line is at least 1 LC, and one player can put
at most 50 lines and 10,000 LC on a round (`engine.MIN_LINE`, `MAX_LINES`,
`MAX_ROUND_TOTAL`). Each line keeps its own `payout`.

| Error | Status | When |
| --- | --- | --- |
| `round_closed` | 409 | a bet outside the betting window |
| `invalid_bet` | 400 | a bet the table doesn't have, or an amount with more than 2 decimals |
| `bet_out_of_range` | 400 | a line under 1 LC or over the round's limit |
| `too_many_lines` | 400 | more than 50 lines in the round |
| `round_limit_exceeded` | 400 | more than 10,000 LC in the round |

### WebSocket

`/ws/roulette` works like `/ws/crash`: no login, read-only, the `Origin` must be one of
`CSRF_TRUSTED_ORIGINS`. It sends only data, never texts.

| `type` | Fields |
| --- | --- |
| `snapshot` | `round`, `history` (the last 14 as `{number, result, color}`, newest first), `bets`, `server_time` |
| `round.betting` | `number`, `status`, `seed_hash`, `betting_ends_at`, `server_time` |
| `round.spinning` | those, and `spin_started_at`, `spin_ends_at`, `result`, `color` |
| `round.settled` | those, and `seed`, `settled_at`, `winning` (the outside bets the result won), `payouts` |
| `bet.placed` | `id`, `round`, `seat`, `player`, `is_bot`, `amount`, `payout`, `lines` |

`round` in a snapshot has the fields of the matching round event, and `bets` those of
`bet.placed`, with their `payout` after the settlement. `payouts` has one row per seat:
`seat`, `player`, `is_bot`, `amount`, `payout`. A player's slips share a `seat`, and
`GET /api/roulette_bets` returns it too, so the frontend can find its own row. The
wheel's order is `engine.WHEEL`.

The bots are like Neon Crash's: admin → Roulette bot settings. They live in
`RouletteBotBet` with no user, and they place real bets of 1 to 3 lines.

## Zeus Legacy

All the maths is in `slots/engine.py` and can't be changed in the admin: 6 columns by 5
rows, 8 or more of a symbol anywhere pay, wins tumble, 4+ scatters give 15 free spins (+5
during free spins), and a spin pays at most 1000x. The first spin of a bonus buy costs
100x the bet, has no multipliers and pays at most 10x. Bets are 0.20 to 100 LC.

`result` is `{spins, total_win, free_spins_played, bonus_buy}`. Each spin has `steps`, one
per tumble (`grid`, `wins`, `winning_cells`, `pay`, `running_win`), and `win`,
`scatter_win`, `collected_multipliers`, `global_multiplier`, `free_spins_awarded`,
`free_spins_left`, `is_max_win`. **Pays in `result` are in hundredths of the bet**: 150 means 1.5x.
Multiply by `amount` for LC. The LC that were really paid are in `payout`.

| Measured | Rounds | Game | Jackpots | Total |
| --- | --- | --- | --- | --- |
| Base game | 5,000,000 | 95.85% | 0.74% (by formula) | 96.6% ± 0.65% |
| Bonus buy | 300,000 | 96.45% | 0.71% | 97.2% ± 0.4% |

A jackpot pool pays back about twice its share of the stakes, so all four give about
0.74%. The grand one is too rare to show in a simulation of this size, which measured
0.59%, so the table uses the formula for the base game. To measure again:

```bash
python manage.py simulate_zeus --rounds 5000000 --workers 10
python manage.py simulate_zeus --rounds 300000 --bonus-buy --workers 10
```

### Sounds

Sound files are not in the repo (`media/sounds/` is git-ignored). This downloads the
original Zeus Legacy sounds from Mixkit into `media/sounds/zeus/` and creates their
`SlotSound` rows:

```bash
python manage.py load_sounds           # only the codes that have no file yet
python manage.py load_sounds --force   # also replace the existing files
```

To change a sound, upload another one in the admin (Slot sounds): MP3, OGG or WAV, 10 MB at
most. `load_sounds` keeps it unless you pass `--force`. The frontend plays only what
`/api/slot_sounds` returns, so a sound without a file is simply silent. `load_sample`
doesn't touch them. The codes are:

| Code | When |
| --- | --- |
| `stone_tumble` | stones fall |
| `sparkle_win` | a win appears |
| `lightning_hit` | lightning |
| `epic_drop` | a big drop |
| `free_spins_theme` | free spins music |
| `big_win` | big win |
| `mega_win` | mega win |
| `ultra_win` | ultra win |
| `symbol_explode` | a symbol explodes |
| `collect_multiplier` | a multiplier is collected |
| `win_tick` | the win counts up |
| `scatter_impact` | a scatter lands |

## Apps

| App | What it owns |
| --- | --- |
| `accounts` | `User` (logs in with email), register, me, login, refresh and logout with JWT cookies (`authentication.py`, `cookies.py`), `LoginPageLabel` |
| `header` | `Logo`, `Language`, `SidebarItem`, `HeaderLabel` |
| `errors` | `ErrorMessage`, `CodedError`, the DRF exception handler, the list of codes |
| `wallet` | `Wallet`, append-only `Transaction` ledger, `JackpotPool`, `services.py` (the only code that moves money), daily bonus |
| `fairness` | provably fair RNG (`rng.py`), `SeedPair`, `services.py` (next nonce, seed rotation), hash chains for shared rounds (`chain.py`, abstract `HashChain`) |
| `games` | `Game` catalogue, `GameCategory`, `LobbyPageLabel` |
| `crash` | Live Neon Crash: `engine.py` (pure maths), `services.py` (bets, cash-outs, round changes), `runner.py` and `run_crash` (the loop), `bots.py`, `feed.py` and `consumers.py` (WebSocket), `CrashChain`, `CrashRound`, `RoundBet`, `CrashBotBet`, `CrashBotSettings`, `CrashPageLabel` |
| `roulette` | Live Lumora Roulette: `engine.py` (pure maths), `services.py` (bets, round changes), `runner.py` and `run_roulette` (the loop), `bots.py`, `feed.py` and `consumers.py` (WebSocket), `RouletteChain`, `RouletteRound`, `RouletteSlip`, `RouletteLine`, `RouletteBotBet`, `RouletteBotSettings`, `RoulettePageLabel` |
| `slots` | Zeus Legacy: `engine.py` (pure maths), `services.py` (plays a round), `simulation.py`, `SlotSpin`, `SlotSymbol`, `SlotSymbolName`, `SlotSound`, `ZeusPageLabel` |
| `leaderboard` | weekly leaderboard from the ledger |
| `sports` | Football data: `Competition`, `Season`, `Team` (+ `TeamName`, `TeamAlias`), `Match`, `Standing`, `SyncRun`; `providers/` (football-data.org adapter, rate limiter, crests), `services.py` (the sync), `runner.py`, `sync_football` and `run_sports`; `SportsPageLabel` |

`base/` holds the settings, the URLs (`OptionalSlashRouter`),
`FilteredReadOnlyViewSet`, `LangFilteredViewSet`, `SingleObjectViewSet`, what the live
games share (`live.py`, `consumers.py`), the constants
(signup grant, daily bonus, languages), `language.py`, image validation (`fields.py`),
media URLs (`serializers.py`, `renderers.py`), `ImagePreviewMixin` and `load_sample`
(`sample.py`, `sample_db.json`).

## Tests

```bash
python manage.py test              # everything except the slow tests, about 2 min
python manage.py test --tag slow   # only the 1,000,000-round Zeus Legacy simulation, about 3 min
```

Every app has its tests in `tests.py`. They run on a temporary PostgreSQL
database (`test_lumora`), so your data is not touched. They check the money
rules (ledger always equals balance, no overspending, idempotency keys, daily
bonus), two 200,000-round simulations that Neon Crash pays back about 97%, one of
them on a real hash chain, the exact RTP of 36/37 for every roulette bet, a 200,000-spin
roulette simulation, that a round can be verified after the seed is revealed, the API rules, CORS and that every admin page
opens. The tests need no Redis: `base.test_runner` swaps in `InMemoryChannelLayer`. `ApiContractTests`
checks that every collection in `base/sample_db.json` has an endpoint that returns
exactly the sample in every language, with and without a trailing slash.
`WalletConcurrencyTests` sends 30 bets of 500 LC at the same moment on real
PostgreSQL connections to a 10,000 LC wallet: exactly 20 must succeed.
`CashOutRaceTests` runs cash-outs against the crash the same way, and `WebSocketTests`
follows a round through `WebsocketCommunicator`. Roulette has the same kinds of tests.
A test tagged
`slow` is skipped by `base.test_runner.SkipSlowTestsRunner` unless `--tag slow` asks
for it. Run the slow tests after changing `slots/engine.py`.

## Production

Set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_BASE_URL` and `EMAIL_BACKEND`
and `CHANNEL_REDIS_URL` in `.env`. `/media/` must be served by the web server, because
Django serves it only in `DEBUG`. Serve the site with `daphne base.asgi:application`,
because WSGI has no WebSocket, and keep one `run_crash`, one `run_roulette` and one
`run_sports` running. Serve `/media/` with the same `Content-Security-Policy` as
`base/media.py`.
With `DEBUG=False` the browsable API is turned off and HTTPS, secure cookies
and HSTS are enabled. Run `python manage.py check --deploy` and
`python manage.py collectstatic` before deploying.
