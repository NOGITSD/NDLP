"""In-memory session store with per-session EVC engine instances."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class SessionState:
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    engine: Any = None
    turn: int = 0
    data: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    def __init__(self, engine_factory: Callable[[], Any]) -> None:
        self._engine_factory = engine_factory
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            state = SessionState(
                session_id=session_id,
                engine=self._engine_factory(),
            )
            self._sessions[session_id] = state
        state.turn = int(getattr(state.engine, "turn", state.turn))
        state.updated_at = datetime.now(timezone.utc)
        return state

    def reset(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def serialize(self, session_id: str) -> dict[str, Any]:
        state = self.get_or_create(session_id)
        engine_state = state.engine.get_full_state() if state.engine is not None else {}
        latest_turn = state.data.get("latest_turn", {})
        return {
            "session_id": state.session_id,
            "turn": int(getattr(state.engine, "turn", state.turn)),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "evc_state": engine_state,
            "latest_turn": latest_turn,
        }
