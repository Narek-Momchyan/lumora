# Lumora

Lumora is a casino-style gaming platform that uses **only demo coins**.
Lumora Coins (LC) have no cash value: there are no deposits, no withdrawals and
no real money. Every player gets 10,000 LC on sign up and a 5,000 LC daily bonus.
Every result is provably fair.

Games: Neon Crash, Zeus Legacy (slot) and Lumora Roulette. Sports predictions and
a mobile app (React Native) come later.

```text
frontend/   Next.js 16 + TypeScript + Tailwind CSS
backend/    Django REST API, admin, PostgreSQL
```

## Run the project

Requirements: Python 3.12+, Pipenv, PostgreSQL 16+, Node.js 20+ and Git.

0. Create the PostgreSQL user and database once:
   [backend/README.md](backend/README.md#create-the-database-once).

1. Backend (first terminal):

```bash
cd backend
pipenv install
copy .env.example .env        # then set SECRET_KEY and DB_PASSWORD
pipenv shell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

2. Frontend (second terminal):

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

On macOS/Linux use `cp` instead of `copy`.

- Site: <http://localhost:3000>
- API: <http://127.0.0.1:8000/api/>
- Admin: <http://127.0.0.1:8000/admin/>

Design: Figma file "Lumora — Web Design".
Details: [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).
