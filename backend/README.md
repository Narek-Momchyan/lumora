# Lumora backend

Django + Django REST Framework API for Lumora, a casino-style gaming platform that
uses only demo coins (Lumora Coins, LC). LC has no cash value: there are no
deposits, withdrawals or real-money features.

## Requirements

- Python 3.12 or newer
- Pipenv (`pip install pipenv`)
- PostgreSQL 16 or newer

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

Run `pipenv shell` in every new terminal (in Git Bash use `cp` instead of
`copy`). The environment lives in `backend/.venv`; to keep it there, set the
environment variable `PIPENV_VENV_IN_PROJECT=1`. `migrate` also adds the game
catalogue (migration `games/0002_seed_games`).

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
```

Use `127.0.0.1`, not `localhost`: Node.js may resolve `localhost` to IPv6
(`::1`), while `runserver` listens on IPv4 only.

## API rules

- `/api/<name>`, with or without a trailing slash.
- Lists are plain JSON arrays without pagination. Feeds return only the newest
  rows: `transactions` the last 100, `crash_bets` and `seeds` the last 50.
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
  `languages`, `sidebar_items`, `header_labels`, `login_page_labels`,
  `lobby_page_labels`, `game_categories`, `slot_symbols`, `slot_symbol_names`,
  `slot_sounds`, `jackpot_pools` and `zeus_page_labels`.
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
| GET | `/api/crash_bets` | cookie | the player's Neon Crash rounds, newest first |
| POST | `/api/crash_bets` | cookie | `{amount, target}` → plays one round at once (auto cash-out at `target`) |
| GET | `/api/seeds` | cookie | the player's provably fair seed pairs, the active one first |
| POST | `/api/seeds` | cookie | `{client_seed?}` → reveals the active server seed and starts a new pair: `{revealed, active}` |
| GET | `/api/leaderboard` | – | top 20 of the last 7 days by net game result |
| GET | `/api/logos` | – | the logo as one object, `{}` before one is added |
| GET | `/api/languages` | – | languages for the language switcher, in `order` |
| GET | `/api/sidebar_items` | – | sidebar links with their `order` and `is_soon`; `?lang=` |
| GET | `/api/header_labels` | – | every text of the sidebar and the header; `?lang=` |
| GET | `/api/login_page_labels` | – | every text of the login page; `?lang=` |
| GET | `/api/lobby_page_labels` | – | every text of the lobby page; `?lang=` |
| GET | `/api/game_categories` | – | category names for filters and game cards; `?lang=` |
| GET | `/api/slot_spins` | cookie | the player's last 50 slot rounds, newest first, without `result` |
| POST | `/api/slot_spins` | cookie | `{game, amount, bonus_buy?}` → plays one round with all its free spins: the round, `result`, `balance` and `jackpot_pools` |
| GET | `/api/slot_spins/<id>` | cookie | one round with its `result` |
| GET | `/api/slot_symbols` | – | slot symbols with their images |
| GET | `/api/slot_symbol_names` | – | symbol names; `?lang=` |
| GET | `/api/slot_sounds` | – | active sounds that have an uploaded file |
| GET | `/api/jackpot_pools` | – | the current amount of each jackpot tier |
| GET | `/api/zeus_page_labels` | – | every text of the Zeus Legacy page; `?lang=` |
| GET | `/api/error_messages` | – | error texts; `?lang=`, `?code=` |

`bonus_available_at` is `null` before the first bonus; a time in the past means
the bonus can be claimed now.

## Content and languages

Site texts and images are edited in the admin and read from the API, never written
in the frontend. Content models have a `lang` field (`base.constants.LANG_CHOICES`);
collections extend `base.views.LangFilteredViewSet`. An unknown `?lang=` returns `[]`
with 200, like any filter; an unknown `lang` cookie means English.

```bash
python manage.py load_sample
```

Fills every collection of `base.sample.COLLECTIONS` from `base/sample_db.json` in en,
am and ru (`--path` loads another file). It **replaces** those tables, so edits made
in the admin are lost; it never touches players, wallets, bets or games. To add a collection: add the model, its endpoint, a key in
`sample_db.json` and a row in `base.sample.COLLECTIONS`.

Images are plain `FileField`s with `base.fields.IMAGE_VALIDATORS`: JPG, PNG, WEBP or
GIF, 5 MB at most, and the file's first bytes must match a real image. SVG is not
allowed, because `/media/` is served from the site's own origin and an SVG can carry
scripts. Files live in `media/`; `runserver` serves them only with `DEBUG=True`.

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
`POST /api/seeds` the old `server_seed` is revealed, and anyone can check a
Neon Crash round:

1. `sha256(server_seed) == server_seed_hash` of the bet;
2. `crash.engine.crash_point(fairness.rng.first_float(server_seed, client_seed, nonce))`
   equals the bet's `crash_point`.

A revealed pair was used for nonces `0` to `nonce - 1`.

A slot round uses one nonce for everything, free spins included. To check one:

```python
stream = float_stream(server_seed, client_seed, nonce)
tier = slots.engine.roll_jackpot(cost, next(stream))
result = slots.engine.play_round(stream, bonus_buy=bonus_buy)
```

`result` equals the saved one, and `tier` equals `jackpot_tier`. The seeds prove only the
jackpot **tier**, not its amount: a pool is shared by all players and grows with their
stakes, so the amount that was paid is saved in `jackpot_win`.

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

Sound files are not in the repo. Upload them in the admin (Slot sounds): MP3, OGG or WAV,
10 MB at most. The frontend plays only what `/api/slot_sounds` returns, so a sound without
a file is simply silent. `load_sample` doesn't touch them. The codes are:

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
| `fairness` | provably fair RNG (`rng.py`), `SeedPair`, `services.py` (next nonce, seed rotation) |
| `games` | `Game` catalogue, `GameCategory`, `LobbyPageLabel` |
| `crash` | Neon Crash: `engine.py` (pure maths), `services.py` (plays a round), `CrashBet` |
| `roulette` | European roulette `engine.py` (maths only, the API comes in phase 3) |
| `slots` | Zeus Legacy: `engine.py` (pure maths), `services.py` (plays a round), `simulation.py`, `SlotSpin`, `SlotSymbol`, `SlotSymbolName`, `SlotSound`, `ZeusPageLabel` |
| `leaderboard` | weekly leaderboard from the ledger |

`base/` holds the settings, the URLs (`OptionalSlashRouter`),
`FilteredReadOnlyViewSet`, `LangFilteredViewSet`, `SingleObjectViewSet`, the constants
(signup grant, daily bonus, languages), `language.py`, image validation (`fields.py`),
media URLs (`serializers.py`, `renderers.py`), `ImagePreviewMixin` and `load_sample`
(`sample.py`, `sample_db.json`).

## Tests

```bash
python manage.py test              # everything except the slow tests, about 10 s
python manage.py test --tag slow   # only the 1,000,000-round Zeus Legacy simulation, about 3 min
```

Every app has its tests in `tests.py`. They run on a temporary PostgreSQL
database (`test_lumora`), so your data is not touched. They check the money
rules (ledger always equals balance, no overspending, idempotency keys, daily
bonus), a 200,000-round simulation that Neon Crash pays back about 97%, the
exact roulette RTP of 36/37, that a round can be verified after the seed is
revealed, the API rules, CORS and that every admin page opens. `ApiContractTests`
checks that every collection in `base/sample_db.json` has an endpoint that returns
exactly the sample in every language, with and without a trailing slash.
`WalletConcurrencyTests` sends 30 bets of 500 LC at the same moment on real
PostgreSQL connections to a 10,000 LC wallet: exactly 20 must succeed. A test tagged
`slow` is skipped by `base.test_runner.SkipSlowTestsRunner` unless `--tag slow` asks
for it. Run the slow tests after changing `slots/engine.py`.

## Production

Set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `PUBLIC_BASE_URL` and `EMAIL_BACKEND`
in `.env`. `/media/` must be served by the web server, because Django serves it only
in `DEBUG`.
With `DEBUG=False` the browsable API is turned off and HTTPS, secure cookies
and HSTS are enabled. Run `python manage.py check --deploy` and
`python manage.py collectstatic` before deploying.
