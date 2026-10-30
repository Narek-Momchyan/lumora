# Lumora backend

Django + Django REST Framework API for Lumora, a casino-style gaming platform that
uses only demo coins (Lumora Coins, LC). LC has no cash value: there are no
deposits, withdrawals or real-money features.

## Requirements

- Python 3.12 or newer
- Pipenv
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
pipenv install
copy .env.example .env        # then set SECRET_KEY and DB_PASSWORD
pipenv shell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- API: http://127.0.0.1:8000/api/
- Admin: http://127.0.0.1:8000/admin/

`migrate` also adds the game catalogue (migration `games/0002_seed_games`).
`pipenv install` creates `Pipfile.lock` on the first run; commit it.

## Connecting the frontend

In `frontend/.env.local` (copied from `frontend/.env.example`):

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
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
- Errors: `{"detail": "..."}`, or `{"<field>": ["..."]}` for a bad field.
- Every endpoint needs a JWT except `register`, `token`, `token/refresh`,
  `games` and `leaderboard`. Send it as `Authorization: Bearer <access>`.
  The access token lives 30 minutes, the refresh token 7 days.

## Endpoints

| Method | URL | Login | What it does |
| --- | --- | --- | --- |
| POST | `/api/register` | – | `{email, password, display_name?}` → new player and a wallet with 10,000 LC |
| POST | `/api/token` | – | `{email, password}` → `{access, refresh}` |
| POST | `/api/token/refresh` | – | `{refresh}` → `{access}` |
| GET | `/api/me` | JWT | the logged-in player |
| GET | `/api/wallet` | JWT | `{balance, last_bonus_at, bonus_available_at, updated_at}` |
| GET | `/api/transactions` | JWT | the player's ledger, newest first |
| POST | `/api/bonus` | JWT | daily bonus of 5,000 LC; `409` with `available_at` if claimed in the last 24 hours |
| GET | `/api/games` | – | active games |
| GET | `/api/crash_bets` | JWT | the player's Neon Crash rounds, newest first |
| POST | `/api/crash_bets` | JWT | `{amount, target}` → plays one round at once (auto cash-out at `target`) |
| GET | `/api/seeds` | JWT | the player's provably fair seed pairs, the active one first |
| POST | `/api/seeds` | JWT | `{client_seed?}` → reveals the active server seed and starts a new pair: `{revealed, active}` |
| GET | `/api/leaderboard` | – | top 20 of the last 7 days by net game result |

`bonus_available_at` is `null` before the first bonus; a time in the past means
the bonus can be claimed now.

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

## Apps

| App | What it owns |
| --- | --- |
| `accounts` | `User` (logs in with email), register, me, JWT token URLs |
| `wallet` | `Wallet`, append-only `Transaction` ledger, `services.py` (the only code that moves money), daily bonus |
| `fairness` | provably fair RNG (`rng.py`), `SeedPair`, `services.py` (next nonce, seed rotation) |
| `games` | `Game` catalogue |
| `crash` | Neon Crash: `engine.py` (pure maths), `services.py` (plays a round), `CrashBet` |
| `roulette` | European roulette `engine.py` (maths only, the API comes in phase 3) |
| `slots` | empty for now: Zeus Legacy moves here in phase 4 |
| `leaderboard` | weekly leaderboard from the ledger |

`base/` holds the settings, the URLs (`OptionalSlashRouter`),
`FilteredReadOnlyViewSet`, `SingleObjectViewSet` and the constants (signup
grant, daily bonus).

## Tests

```bash
python manage.py test
```

Every app has its tests in `tests.py`. They run on a temporary PostgreSQL
database (`test_lumora`), so your data is not touched. They check the money
rules (ledger always equals balance, no overspending, idempotency keys, daily
bonus), a 200,000-round simulation that Neon Crash pays back about 97%, the
exact roulette RTP of 36/37, that a round can be verified after the seed is
revealed, the API rules, CORS and that every admin page opens.
`WalletConcurrencyTests` sends 30 bets of 500 LC at the same moment on real
PostgreSQL connections to a 10,000 LC wallet: exactly 20 must succeed.

## Production

Set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` and `EMAIL_BACKEND` in `.env`.
With `DEBUG=False` the browsable API is turned off and HTTPS, secure cookies
and HSTS are enabled. Run `python manage.py check --deploy` and
`python manage.py collectstatic` before deploying.
