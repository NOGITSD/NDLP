"""
Authentication module — JWT tokens, password hashing, user management.
Supports: local (user/pass), Google OAuth (future), guest mode.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone
from typing import Optional

from .db.base_repository import BaseRepository, UserDTO, PlatformIdentityDTO

# ── Config ────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "jarvis-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
GUEST_EXPIRY_SECONDS = 60 * 60 * 24    # 1 day for guests


# ── Password hashing (simple bcrypt-like with hmac+sha256) ──────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if ":" not in stored_hash:
        return False
    salt, expected = stored_hash.split(":", 1)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return hmac.compare_digest(h.hex(), expected)


# ── Simple JWT (no external deps) ──────────────────────────────────

def _b64e(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return urlsafe_b64decode(s + "=" * pad)


def _hmac_sign(payload: str) -> str:
    sig = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    return _b64e(sig)


def create_jwt(user_id: str, is_guest: bool = False, extra: dict = None) -> str:
    now = int(time.time())
    expiry = GUEST_EXPIRY_SECONDS if is_guest else JWT_EXPIRY_SECONDS
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + expiry,
        "guest": is_guest,
    }
    if extra:
        payload.update(extra)
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64e(json.dumps(payload).encode())
    signature = _hmac_sign(f"{header}.{body}")
    return f"{header}.{body}.{signature}"


def decode_jwt(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        expected_sig = _hmac_sign(f"{header}.{body}")
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(_b64d(body))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# ── Auth Service ─────────────────────────────────────────────────────

class AuthService:
    def __init__(self, repo: BaseRepository):
        self.repo = repo

    def register(self, username: str, password: str,
                 email: str = None, display_name: str = "") -> tuple[UserDTO, str]:
        """Register a new local user. Returns (user, jwt_token)."""
        if self.repo.get_user_by_username(username):
            raise ValueError("Username already exists")
        if email and self.repo.get_user_by_email(email):
            raise ValueError("Email already exists")

        user = UserDTO(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            display_name=display_name or username,
            password_hash=hash_password(password),
            auth_provider="local",
            is_guest=False,
        )
        self.repo.create_user(user)

        # Create web platform identity
        self.repo.create_platform_identity(PlatformIdentityDTO(
            id=str(uuid.uuid4()),
            user_id=user.id,
            platform="web",
            platform_uid=user.id,
            platform_name=user.display_name,
        ))

        self.repo.update_last_login(user.id)
        token = create_jwt(user.id, is_guest=False)
        return user, token

    def login(self, username: str, password: str) -> tuple[UserDTO, str]:
        """Login with username/password. Returns (user, jwt_token)."""
        user = self.repo.get_user_by_username(username)
        if not user:
            user = self.repo.get_user_by_email(username)
        if not user or not user.password_hash:
            raise ValueError("Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account is deactivated")

        self.repo.update_last_login(user.id)
        token = create_jwt(user.id, is_guest=False)
        return user, token

    def create_guest(self) -> tuple[UserDTO, str]:
        """Create a guest user (no persistence across sessions)."""
        guest_id = str(uuid.uuid4())
        user = UserDTO(
            id=guest_id,
            username=None,
            email=None,
            display_name=f"Guest_{guest_id[:8]}",
            auth_provider="guest",
            is_guest=True,
        )
        self.repo.create_user(user)
        token = create_jwt(user.id, is_guest=True)
        return user, token

    def google_login(self, google_id: str, email: str,
                     display_name: str, avatar_url: str = "") -> tuple[UserDTO, str]:
        """Login or register via Google. Returns (user, jwt_token)."""
        # Check if already linked
        user = self.repo.get_user_by_platform("google", google_id)
        if user:
            self.repo.update_last_login(user.id)
            token = create_jwt(user.id, is_guest=False)
            return user, token

        # Check if email exists (link accounts)
        user = self.repo.get_user_by_email(email)
        if user:
            self.repo.create_platform_identity(PlatformIdentityDTO(
                id=str(uuid.uuid4()),
                user_id=user.id,
                platform="google",
                platform_uid=google_id,
                platform_name=display_name,
            ))
            self.repo.update_last_login(user.id)
            token = create_jwt(user.id, is_guest=False)
            return user, token

        # New user from Google
        user = UserDTO(
            id=str(uuid.uuid4()),
            username=email.split("@")[0],
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            auth_provider="google",
            is_guest=False,
        )
        self.repo.create_user(user)
        self.repo.create_platform_identity(PlatformIdentityDTO(
            id=str(uuid.uuid4()),
            user_id=user.id,
            platform="google",
            platform_uid=google_id,
            platform_name=display_name,
        ))
        self.repo.update_last_login(user.id)
        token = create_jwt(user.id, is_guest=False)
        return user, token

    def link_platform(self, user_id: str, platform: str,
                      platform_uid: str, platform_name: str = "") -> PlatformIdentityDTO:
        """Link a new platform (LINE, Discord) to existing user."""
        existing = self.repo.get_user_by_platform(platform, platform_uid)
        if existing and existing.id != user_id:
            raise ValueError(f"Platform account already linked to another user")

        identity = PlatformIdentityDTO(
            id=str(uuid.uuid4()),
            user_id=user_id,
            platform=platform,
            platform_uid=platform_uid,
            platform_name=platform_name,
        )
        self.repo.create_platform_identity(identity)
        return identity

    def get_current_user(self, token: str) -> Optional[UserDTO]:
        """Validate JWT and return user."""
        payload = decode_jwt(token)
        if not payload:
            return None
        return self.repo.get_user_by_id(payload["sub"])

    def upgrade_guest(self, guest_user_id: str, username: str,
                      password: str, email: str = None,
                      display_name: str = "") -> tuple[UserDTO, str]:
        """Convert a guest account to a full account."""
        user = self.repo.get_user_by_id(guest_user_id)
        if not user or not user.is_guest:
            raise ValueError("Not a guest account")
        if self.repo.get_user_by_username(username):
            raise ValueError("Username already exists")

        user.username = username
        user.email = email
        user.display_name = display_name or username
        user.password_hash = hash_password(password)
        user.auth_provider = "local"
        user.is_guest = False
        self.repo.update_user(user)

        token = create_jwt(user.id, is_guest=False)
        return user, token
