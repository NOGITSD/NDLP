"""
Database factory — creates the right repository based on config.
Set DB_BACKEND env var: 'sqlite' (default) | 'firebase'
"""

from __future__ import annotations

import os
from .base_repository import BaseRepository


def create_repository() -> BaseRepository:
    backend = os.getenv("DB_BACKEND", "sqlite").lower()

    if backend == "firebase":
        from .firebase_repository import FirebaseRepository
        return FirebaseRepository()
    else:
        db_path = os.getenv("DB_PATH", "data/jarvis.db")
        from .sqlite_repository import SQLiteRepository
        return SQLiteRepository(db_path=db_path)
