# Backend Phase 1 Setup

## 1) Create virtual environment (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2) Install dependencies
```powershell
pip install -r backend/requirements.txt
```

## 3) Configure environment
```powershell
copy backend/.env.example backend/.env
# then edit backend/.env and set GROQ_API_KEY
```

## 4) Run API server
```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 5) Quick checks
- Health: `GET http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- Chat endpoint: `POST /api/chat`

## Generated Phase 1 files
- `backend/main.py`
- `backend/groq_bridge.py`
- `backend/prompts.py`
- `backend/session_manager.py`
- `backend/requirements.txt`
- `backend/.env.example`
