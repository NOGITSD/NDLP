from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

# Make EVC engine modules importable from project_jarvis/
ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_JARVIS_DIR = ROOT_DIR / "project_jarvis"
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(PROJECT_JARVIS_DIR) not in sys.path:
    sys.path.append(str(PROJECT_JARVIS_DIR))

from .groq_bridge import GroqBridge
from .session_manager import SessionManager
from .memory_manager import MemoryManager
from .skill_manager import SkillManager
from .auth import AuthService, decode_jwt
from .db.factory import create_repository
from .db.base_repository import UserDTO, MessageDTO, ConversationDTO
from .user_memory import UserMemoryService
from evc_core import EVCEngine
from config import HORMONE_NAMES, EMOTION_NAMES
from .user_emotion_tracker import UserEmotionTracker
try:
    from .test_messages import TEST_MESSAGES_100
except ImportError:
    TEST_MESSAGES_100 = []

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=True)

app = FastAPI(title="Project Jarvis API", version="0.1.0")

# ── Database & Auth ──
db_repo = create_repository()
auth_service = AuthService(db_repo)

TURN_SECONDS = 300.0  # 1 turn ~= 5 minutes of real time
MIN_DELTA_T = 0.05    # floor to keep dynamics moving even in rapid-fire tests
MAX_DELTA_T = 12.0    # cap for long inactivity gaps

_cors_origins = os.getenv("FRONTEND_ORIGIN", "*")
_allowed_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _compute_delta_t_turns(state: Any, now_ts: float) -> float:
    """Compute elapsed time in turn units from previous turn timestamp."""
    last_ts = state.data.get("last_turn_ts")
    state.data["last_turn_ts"] = now_ts
    if last_ts is None:
        return 1.0
    elapsed_sec = max(now_ts - float(last_ts), 0.0)
    delta_t = elapsed_sec / TURN_SECONDS
    return _clamp(delta_t, MIN_DELTA_T, MAX_DELTA_T)


def create_evc_engine() -> EVCEngine:
    return EVCEngine(name="Jarvis")


DATA_DIR = str(ROOT_DIR / "data" / "users")
SKILLS_DIR = str(ROOT_DIR / "skills")

sessions = SessionManager(engine_factory=create_evc_engine)
groq = GroqBridge()
skills = SkillManager(skills_dir=SKILLS_DIR)

# Per-session memory managers (lazy init)
_memory_managers: dict[str, MemoryManager] = {}

# Per-user memory service cache
_user_memory_services: dict[str, UserMemoryService] = {}


def _get_memory(session_id: str) -> MemoryManager:
    if session_id not in _memory_managers:
        mm = MemoryManager(user_id=session_id, data_dir=DATA_DIR)
        mm.reindex_all()
        _memory_managers[session_id] = mm
    return _memory_managers[session_id]


def _get_user_memory(user_id: str) -> UserMemoryService:
    if user_id not in _user_memory_services:
        _user_memory_services[user_id] = UserMemoryService(db_repo, user_id)
    return _user_memory_services[user_id]


# ── Auth dependency ──

def _optional_user(authorization: str = Header(default="")) -> UserDTO | None:
    """Extract user from JWT if present. Returns None for unauthenticated requests."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    payload = decode_jwt(token)
    if not payload:
        return None
    return db_repo.get_user_by_id(payload["sub"])


def _require_user(authorization: str = Header(default="")) -> UserDTO:
    """Require a valid JWT. Raises 401 if not authenticated."""
    user = _optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Request/Response models ──

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ResetRequest(BaseModel):
    session_id: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    email: str | None = None
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LearnFactRequest(BaseModel):
    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    category: str = "general"


class UpgradeGuestRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    email: str | None = None
    display_name: str = ""


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=1)  # Google ID token from frontend


# ── Health ──

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_runtime_config() -> dict[str, Any]:
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
    }


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/register")
def auth_register(payload: RegisterRequest) -> dict[str, Any]:
    try:
        user, token = auth_service.register(
            username=payload.username,
            password=payload.password,
            email=payload.email,
            display_name=payload.display_name or payload.username,
        )
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "display_name": user.display_name,
                     "email": user.email, "is_guest": user.is_guest, "auth_provider": user.auth_provider},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest) -> dict[str, Any]:
    try:
        user, token = auth_service.login(payload.username, payload.password)
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "display_name": user.display_name,
                     "email": user.email, "is_guest": user.is_guest, "auth_provider": user.auth_provider},
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/google")
def auth_google(payload: GoogleLoginRequest) -> dict[str, Any]:
    """Verify Google ID token and login/register the user."""
    import httpx

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        raise HTTPException(status_code=501, detail="Google login not configured (GOOGLE_CLIENT_ID missing)")

    # Verify token with Google
    try:
        resp = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.credential},
            timeout=10.0,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        ginfo = resp.json()

        # Verify audience matches our client ID
        if ginfo.get("aud") != google_client_id:
            raise HTTPException(status_code=401, detail="Token audience mismatch")

        google_id = ginfo.get("sub", "")
        email = ginfo.get("email", "")
        name = ginfo.get("name", email.split("@")[0])
        picture = ginfo.get("picture", "")

        if not google_id or not email:
            raise HTTPException(status_code=401, detail="Incomplete Google profile")

        user, token = auth_service.google_login(
            google_id=google_id,
            email=email,
            display_name=name,
            avatar_url=picture,
        )
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "display_name": user.display_name,
                     "email": user.email, "is_guest": user.is_guest, "auth_provider": user.auth_provider,
                     "avatar_url": user.avatar_url},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google auth failed: {str(e)}")


@app.post("/api/auth/guest")
def auth_guest() -> dict[str, Any]:
    user, token = auth_service.create_guest()
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "display_name": user.display_name,
                 "is_guest": user.is_guest, "auth_provider": user.auth_provider},
    }


@app.post("/api/auth/upgrade-guest")
def auth_upgrade_guest(payload: UpgradeGuestRequest,
                       user: UserDTO = Depends(_require_user)) -> dict[str, Any]:
    try:
        updated_user, token = auth_service.upgrade_guest(
            guest_user_id=user.id,
            username=payload.username,
            password=payload.password,
            email=payload.email,
            display_name=payload.display_name or payload.username,
        )
        return {
            "token": token,
            "user": {"id": updated_user.id, "username": updated_user.username,
                     "display_name": updated_user.display_name, "email": updated_user.email,
                     "is_guest": updated_user.is_guest, "auth_provider": updated_user.auth_provider},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/me")
def auth_me(user: UserDTO = Depends(_require_user)) -> dict[str, Any]:
    return {
        "id": user.id, "username": user.username, "display_name": user.display_name,
        "email": user.email, "is_guest": user.is_guest, "auth_provider": user.auth_provider,
        "avatar_url": user.avatar_url, "created_at": user.created_at,
    }


# ---------------------------------------------------------------------------
# User Memory endpoints (bot knowledge about user)
# ---------------------------------------------------------------------------

@app.get("/api/user/facts")
def get_user_facts(category: str = None,
                  user: UserDTO = Depends(_require_user)) -> list[dict]:
    um = _get_user_memory(user.id)
    facts = um.get_facts_by_category(category) if category else um.get_all_facts()
    return [{"id": f.id, "category": f.category, "key": f.key, "value": f.value,
             "confidence": f.confidence, "mention_count": f.mention_count,
             "last_confirmed": f.last_confirmed} for f in facts]


@app.post("/api/user/facts")
def learn_user_fact(payload: LearnFactRequest,
                   user: UserDTO = Depends(_require_user)) -> dict[str, Any]:
    um = _get_user_memory(user.id)
    fact = um.learn_fact(key=payload.key, value=payload.value,
                        category=payload.category, source="explicit", confidence=1.0)
    return {"id": fact.id, "key": fact.key, "value": fact.value, "category": fact.category}


@app.delete("/api/user/facts/{fact_id}")
def delete_user_fact(fact_id: str,
                    user: UserDTO = Depends(_require_user)) -> dict[str, bool]:
    um = _get_user_memory(user.id)
    return {"deleted": um.forget_fact(fact_id)}


@app.get("/api/user/profile-context")
def get_user_profile_context(user: UserDTO = Depends(_require_user)) -> dict[str, str]:
    um = _get_user_memory(user.id)
    return {"context": um.build_user_profile_context()}


@app.get("/api/user/conversations")
def list_user_conversations(limit: int = 50,
                            user: UserDTO = Depends(_require_user)) -> list[dict]:
    convs = db_repo.list_conversations(user.id, limit=limit)
    return [{"id": c.id, "title": c.title, "platform": c.platform,
             "created_at": c.created_at, "updated_at": c.updated_at} for c in convs]


@app.get("/api/conversations/{conv_id}/messages")
def get_conversation_messages(conv_id: str, limit: int = 100,
                              user: UserDTO = Depends(_require_user)) -> dict:
    conv = db_repo.get_conversation(conv_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db_repo.get_messages(conv_id, limit=limit)
    # Load saved EVC state so frontend can display hormones/emotions on resume
    evc_state, last_turn_ts = None, None
    try:
        evc_state, last_turn_ts = db_repo.get_evc_state(conv_id)
    except Exception:
        pass
    # Compute time-decayed bot_state for display (without mutating engine)
    bot_state = None
    if evc_state:
        from evc_core import EVCEngine
        from emotions import EmotionMapper
        tmp_engine = EVCEngine()
        tmp_engine.load_state(evc_state)
        # Apply time-based half-life decay preview
        if last_turn_ts:
            elapsed = max(time.time() - float(last_turn_ts), 0.0)
            delta_t = _clamp(elapsed / TURN_SECONDS, MIN_DELTA_T, MAX_DELTA_T)
            # Dry-run decay: simulate a neutral turn to show decayed state
            tmp_engine.hormones.apply_decay(delta_t)
            tmp_engine.hormones.apply_homeostasis()
        emotions = tmp_engine.emotions.compute(tmp_engine.hormones.H)
        dominant_name, dominant_score = tmp_engine.emotions.get_dominant()
        bot_state = {
            "turn": tmp_engine.turn,
            "hormones": tmp_engine.hormones.get_state_dict(),
            "emotions": tmp_engine.emotions.get_state_dict(),
            "dominant_emotion": dominant_name,
            "dominant_score": round(dominant_score, 4),
            "emotion_blend": tmp_engine.emotions.get_emotion_label(),
            "trust": round(float(tmp_engine.trust), 4),
        }
    return {
        "messages": [
            {
                "id": m.id, "role": m.role, "content": m.content,
                "signals_s": m.signals_s, "signals_d": m.signals_d, "signals_c": m.signals_c,
                "dominant_emotion": m.dominant_emotion, "trust_level": m.trust_level,
                "metadata": m.metadata, "created_at": m.created_at,
            }
            for m in msgs
        ],
        "bot_state": bot_state,
    }


@app.post("/api/chat")
def chat(payload: ChatRequest,
         user: UserDTO | None = Depends(_optional_user)) -> dict[str, Any]:
    state = sessions.get_or_create(payload.session_id)
    memory = _get_memory(payload.session_id)
    now_ts = time.time()

    # 0a. Restore EVC state from DB if resuming a conversation (conv_ prefix)
    if (not state.data.get("evc_restored")
            and payload.session_id.startswith("conv_")
            and user and not user.is_guest):
        resume_id = payload.session_id[5:]
        try:
            saved_evc, saved_ts = db_repo.get_evc_state(resume_id)
            if saved_evc:
                state.engine.load_state(saved_evc)
                # Restore user emotion tracker state
                if "user_emotion_tracker" in saved_evc:
                    tracker = UserEmotionTracker()
                    tracker.load_state(saved_evc["user_emotion_tracker"])
                    state.data["user_emotion_tracker"] = tracker
                if saved_ts:
                    state.data["last_turn_ts"] = float(saved_ts)
        except Exception:
            pass  # best-effort
        state.data["evc_restored"] = True

    # 0b. User memory context (if authenticated)
    user_profile_context = ""
    user_memory_context = ""
    if user and not user.is_guest:
        um = _get_user_memory(user.id)
        user_profile_context = um.build_user_profile_context()
        user_memory_context = um.build_memory_context_for_chat()

    # 1. Memory search — retrieve relevant context
    memory_context = memory.build_context(payload.message, max_results=5)
    long_term = memory.get_long_term()

    # Merge user profile into long_term memory
    if user_profile_context:
        long_term = user_profile_context + "\n\n" + long_term
    if user_memory_context:
        memory_context = user_memory_context + "\n\n" + memory_context

    # 2. Skill matching
    matched_skill = skills.match(payload.message)
    skill_context = skills.get_skill_context(matched_skill.name) if matched_skill else ""

    # 3. Analyze sentiment (S, D, C)
    analysis = groq.analyze_message(payload.message)
    S = _clamp(analysis.S, 0.0, 1.0)
    D = _clamp(analysis.D, 0.0, 1.0)
    C = _clamp(analysis.C, 0.5, 1.5)

    # 3b. User Emotion Tracking — record signals and build context
    user_tracker: UserEmotionTracker = state.data.get("user_emotion_tracker")
    if user_tracker is None:
        user_tracker = UserEmotionTracker()
        state.data["user_emotion_tracker"] = user_tracker
    user_tracker.record_turn(
        S=S, D=D, C=C,
        user_emotion=analysis.user_emotion,
        message_preview=payload.message[:60],
    )
    user_emotion_context = user_tracker.build_user_emotion_summary()

    # 4. EVC engine — update hormones/emotions/trust
    # delta_t uses last_turn_ts from DB (if restored), so real elapsed time applies half-life decay
    delta_t = _compute_delta_t_turns(state, now_ts)
    turn_result = state.engine.process_turn(
        S=S,
        D=D,
        C=C,
        delta_t=delta_t,
        message=payload.message,
    )
    state.turn = turn_result["turn"]
    state.data["latest_turn"] = turn_result

    # 5. Build chat history for LLM continuity
    chat_history = state.data.get("chat_history", [])
    # If resuming and history is empty, load from DB
    if not chat_history and payload.session_id.startswith("conv_") and user and not user.is_guest:
        resume_id = payload.session_id[5:]
        try:
            db_msgs = db_repo.get_messages(resume_id, limit=20)
            chat_history = [{"role": m.role, "content": m.content} for m in db_msgs]
        except Exception:
            pass

    # Generate reply with memory + skill + emotion context + history
    reply = groq.generate_reply(
        payload.message,
        turn_result,
        analysis.user_emotion,
        memory_context=memory_context,
        long_term_memory=long_term,
        skill_context=skill_context,
        chat_history=chat_history,
        user_emotion_context=user_emotion_context,
    )
    state.data["last_reply"] = reply

    # Append to in-memory chat history for subsequent turns
    chat_history.append({"role": "user", "content": payload.message})
    chat_history.append({"role": "assistant", "content": reply})
    # Keep last 30 messages to prevent unbounded growth
    state.data["chat_history"] = chat_history[-30:]

    # 6. Write to daily log
    dominant = turn_result.get("dominant_emotion", "Neutral")
    memory.append_daily_log(
        f"[Turn {state.turn}] User: {payload.message[:80]} | "
        f"Emotion: {dominant} | Trust: {turn_result.get('trust', 0):.2f}"
    )

    # 7. Persist messages to DB for authenticated (non-guest) users
    if user and not user.is_guest:
        conv_id = state.data.get("conversation_id")
        # Support resuming: session_id = "conv_{uuid}" means append to existing conversation
        if not conv_id and payload.session_id.startswith("conv_"):
            resume_id = payload.session_id[5:]
            existing = db_repo.get_conversation(resume_id)
            if existing and existing.user_id == user.id:
                conv_id = resume_id
                state.data["conversation_id"] = conv_id
        if not conv_id:
            conv_id = str(uuid.uuid4())
            db_repo.create_conversation(ConversationDTO(
                id=conv_id, user_id=user.id,
                title=payload.message[:50], platform="web",
            ))
            state.data["conversation_id"] = conv_id
        # Save user message
        db_repo.create_message(MessageDTO(
            id=str(uuid.uuid4()), conversation_id=conv_id,
            role="user", content=payload.message,
            signals_s=S, signals_d=D, signals_c=C,
        ))
        # Save bot reply
        db_repo.create_message(MessageDTO(
            id=str(uuid.uuid4()), conversation_id=conv_id,
            role="assistant", content=reply,
            dominant_emotion=dominant,
            trust_level=turn_result.get("trust", 0),
            metadata=json.dumps({"matched_skill": matched_skill.name if matched_skill else None}),
        ))
        # Save EVC state + user emotion tracker state for resuming
        try:
            evc_full = state.engine.get_full_state()
            if user_tracker:
                evc_full["user_emotion_tracker"] = user_tracker.get_state()
            db_repo.save_evc_state(conv_id, evc_full, now_ts)
        except Exception:
            pass  # best-effort

    # 8. Auto-extract facts from user message (non-blocking, best-effort)
    learned_facts = []
    if user and not user.is_guest:
        try:
            raw_facts = groq.extract_facts(payload.message)
            if raw_facts:
                um = _get_user_memory(user.id)
                for f in raw_facts:
                    conf = float(f.get("confidence", 0.7))
                    if conf >= 0.5:
                        um.learn_fact(
                            key=f["key"], value=f["value"],
                            category=f.get("category", "general"),
                            confidence=conf, source="conversation",
                        )
                        learned_facts.append({"key": f["key"], "value": f["value"]})
        except Exception:
            pass  # fact extraction is best-effort

    return {
        "response": reply,
        "user_emotion": analysis.user_emotion,
        "signals": {"S": S, "D": D, "C": C},
        "delta_t": round(delta_t, 4),
        "bot_state": turn_result,
        "matched_skill": matched_skill.name if matched_skill else None,
        "memory_used": bool(memory_context),
        "learned_facts": learned_facts,
        "user_mood": {
            "current": user_tracker.get_current_mood() if user_tracker else "",
            "trend": user_tracker.get_trend() if user_tracker else "",
            "stats": user_tracker.get_emotion_stats() if user_tracker else {},
        },
    }


@app.get("/api/state")
def get_state(session_id: str) -> dict[str, Any]:
    return sessions.serialize(session_id)


@app.post("/api/reset")
def reset(payload: ResetRequest) -> dict[str, Any]:
    deleted = sessions.reset(payload.session_id)
    if payload.session_id in _memory_managers:
        _memory_managers[payload.session_id].close()
        del _memory_managers[payload.session_id]
    return {"status": "ok", "reset": deleted}


@app.get("/api/memory")
def get_memory(session_id: str) -> dict[str, Any]:
    memory = _get_memory(session_id)
    return {
        "long_term": memory.get_long_term(),
        "recent_logs": memory.get_recent_logs(days=2),
    }


@app.get("/api/skills")
def list_skills() -> list[dict[str, str]]:
    return skills.list_skills()


# ---------------------------------------------------------------------------
# Export endpoints — for tuning & analysis
# ---------------------------------------------------------------------------

@app.get("/api/export/history")
def export_history(session_id: str) -> dict[str, Any]:
    """Full turn-by-turn history as JSON (for graph rendering)."""
    state = sessions.get_or_create(session_id)
    return {
        "session_id": session_id,
        "total_turns": state.turn,
        "turns": state.engine.turn_log if state.engine else [],
    }


@app.get("/api/export/txt", response_class=PlainTextResponse)
def export_txt(session_id: str) -> str:
    """Export conversation + hormone/emotion data as readable TXT."""
    state = sessions.get_or_create(session_id)
    log = state.engine.turn_log if state.engine else []
    if not log:
        return "No data to export."

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"  JARVIS EVC Export — Session: {session_id}")
    lines.append(f"  Total turns: {len(log)}")
    lines.append("=" * 70)
    lines.append("")

    for t in log:
        lines.append(f"--- Turn {t['turn']} ---")
        lines.append(f"  Message : {t.get('message', '')}")
        lines.append(f"  Delta_t : {t.get('delta_t', 1.0):.4f} turns")
        inp = t.get('input', {})
        lines.append(f"  Signals : S={inp.get('S',0):.3f}  D={inp.get('D',0):.3f}  C={inp.get('C',1):.3f}")
        lines.append(f"  Emotion : {t.get('emotion_blend', '')}")
        lines.append(f"  Dominant: {t.get('dominant_emotion', '')} ({t.get('dominant_score', 0):.4f})")
        lines.append(f"  Trust   : {t.get('trust', 0):.4f}")

        hormones = t.get('hormones', {})
        h_str = "  ".join(f"{k}={v:.3f}" for k, v in hormones.items())
        lines.append(f"  Hormones: {h_str}")

        emotions = t.get('emotions', {})
        e_str = "  ".join(f"{k}={v:.3f}" for k, v in emotions.items())
        lines.append(f"  Emotions: {e_str}")

        delta = t.get('hormone_delta', {})
        d_str = "  ".join(f"{k}={v:+.4f}" for k, v in delta.items())
        lines.append(f"  H Delta : {d_str}")
        lines.append("")

    return "\n".join(lines)


@app.get("/api/export/csv")
def export_csv(session_id: str):
    """Export as CSV for spreadsheet analysis."""
    state = sessions.get_or_create(session_id)
    log = state.engine.turn_log if state.engine else []

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["turn", "message", "delta_t", "S", "D", "C", "trust", "dominant_emotion", "dominant_score"]
    header += [f"h_{h.lower()}" for h in HORMONE_NAMES]
    header += [f"e_{e.lower()}" for e in EMOTION_NAMES]
    header += [f"dh_{h.lower()}" for h in HORMONE_NAMES]
    writer.writerow(header)

    for t in log:
        inp = t.get('input', {})
        hormones = t.get('hormones', {})
        emotions = t.get('emotions', {})
        delta = t.get('hormone_delta', {})
        row = [
            t['turn'],
            t.get('message', ''),
            t.get('delta_t', 1.0),
            inp.get('S', 0),
            inp.get('D', 0),
            inp.get('C', 1),
            t.get('trust', 0),
            t.get('dominant_emotion', ''),
            t.get('dominant_score', 0),
        ]
        row += [hormones.get(h.lower(), hormones.get(h, 0)) for h in HORMONE_NAMES]
        row += [emotions.get(e, 0) for e in EMOTION_NAMES]
        row += [delta.get(h.lower(), delta.get(h, 0)) for h in HORMONE_NAMES]
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=jarvis_export_{session_id}.csv"},
    )


# ---------------------------------------------------------------------------
# Auto-test mode — run 100 messages sequentially via SSE
# ---------------------------------------------------------------------------

@app.get("/api/autotest/messages")
def autotest_messages() -> list[dict[str, Any]]:
    """Return the 100 test messages (for preview)."""
    return [
        {"index": i, "message": msg, "S": s, "D": d, "C": c}
        for i, (msg, s, d, c) in enumerate(TEST_MESSAGES_100)
    ]


@app.get("/api/autotest/start")
async def autotest_start(
    session_id: str = "autotest",
    use_expected_signals: bool = True,
    delay_seconds: float = 1.5,
):
    """
    Run all 100 test messages sequentially, streaming progress via SSE.
    Each message goes through the FULL pipeline (Groq analyze + EVC + Groq reply).
    Delay between messages to respect Groq rate limits.
    """
    async def event_stream():
        # Reset session for clean test
        sessions.reset(session_id)
        if session_id in _memory_managers:
            _memory_managers[session_id].close()
            del _memory_managers[session_id]

        state = sessions.get_or_create(session_id)
        memory = _get_memory(session_id)
        total = len(TEST_MESSAGES_100)

        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        for i, (msg_text, expected_s, expected_d, expected_c) in enumerate(TEST_MESSAGES_100):
            turn_num = i + 1
            t0 = time.time()

            try:
                # 1. Memory search
                memory_context = memory.build_context(msg_text, max_results=3)
                long_term = memory.get_long_term()

                # 2. Skill matching
                matched_skill = skills.match(msg_text)
                skill_context = skills.get_skill_context(matched_skill.name) if matched_skill else ""

                # 3. Signal extraction (expected set is best for EVC calibration)
                analysis = groq.analyze_message(msg_text)
                if use_expected_signals:
                    S = _clamp(expected_s, 0.0, 1.0)
                    D = _clamp(expected_d, 0.0, 1.0)
                    C = _clamp(expected_c, 0.5, 1.5)
                else:
                    S = _clamp(analysis.S, 0.0, 1.0)
                    D = _clamp(analysis.D, 0.0, 1.0)
                    C = _clamp(analysis.C, 0.5, 1.5)

                # 4. EVC engine
                delta_t = _compute_delta_t_turns(state, time.time())
                turn_result = state.engine.process_turn(
                    S=S, D=D, C=C, delta_t=delta_t, message=msg_text,
                )
                state.turn = turn_result["turn"]
                state.data["latest_turn"] = turn_result

                # 5. Generate reply
                reply = groq.generate_reply(
                    msg_text, turn_result, analysis.user_emotion,
                    memory_context=memory_context,
                    long_term_memory=long_term,
                    skill_context=skill_context,
                )

                # 6. Daily log
                dominant = turn_result.get("dominant_emotion", "Neutral")
                memory.append_daily_log(
                    f"[Turn {state.turn}] User: {msg_text[:60]} | "
                    f"Emotion: {dominant} | Trust: {turn_result.get('trust', 0):.2f}"
                )

                elapsed = round(time.time() - t0, 2)

                progress = {
                    "type": "turn",
                    "turn": turn_num,
                    "total": total,
                    "message": msg_text,
                    "reply": reply[:120],
                    "signals": {"S": round(S, 3), "D": round(D, 3), "C": round(C, 3)},
                    "expected": {"S": expected_s, "D": expected_d, "C": expected_c},
                    "signal_source": "expected" if use_expected_signals else "analyzer",
                    "delta_t": round(delta_t, 4),
                    "dominant_emotion": turn_result.get("dominant_emotion", ""),
                    "trust": round(turn_result.get("trust", 0), 4),
                    "elapsed_sec": elapsed,
                }
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'turn': turn_num, 'error': str(e)})}\n\n"

            # Delay to respect Groq rate limits (1.5s between calls)
            await asyncio.sleep(max(delay_seconds, 0.0))

        # Done
        yield f"data: {json.dumps({'type': 'done', 'total_turns': total, 'session_id': session_id})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Serve frontend static files in production ──
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend_dist"
if _frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="static-assets")

    # SPA catch-all: any non-/api route serves index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))
