# Environment Setup (Docker Deployment)

## 1) Root compose env
Copy `.env.example` to `.env` and set value:

- `VITE_GOOGLE_CLIENT_ID`

## 2) Backend runtime env
Copy `backend/.env.example` to `backend/.env` and fill:

- `GROQ_API_KEY`
- `FRONTEND_ORIGIN`
- `DB_BACKEND`
- `FIREBASE_CREDENTIALS`
- `GOOGLE_CLIENT_ID` (optional)

## 3) Frontend local env (optional for local dev only)
Copy `frontend/.env.example` to `frontend/.env`.

## 4) Firebase service account file
Place your service account JSON in `backend/` and keep filename aligned with:

- `backend/.env -> FIREBASE_CREDENTIALS`
- `docker-compose.yml` volume mount

## 5) Run deploy
```bash
docker compose up -d --build
```

## 6) Verify
- `http://localhost`
- `http://localhost/health`
- `http://localhost:8000/health`
