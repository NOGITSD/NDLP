"""
OpenClaw-style Memory Manager for Project Jarvis.
Ported from openclaw/src/memory/ (TypeScript → Python).

Handles:
- MEMORY.md (long-term user profile/preferences)
- memory/YYYY-MM-DD.md (daily conversation logs)
- Markdown chunking (~400 tokens, 80-token overlap)
- BM25 keyword search over chunks
- SQLite index for fast retrieval
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data classes (mirrors openclaw/src/memory/types.ts)
# ---------------------------------------------------------------------------

@dataclass
class MemoryChunk:
    start_line: int
    end_line: int
    text: str
    hash: str


@dataclass
class MemoryFileEntry:
    rel_path: str
    abs_path: str
    mtime: float
    size: int
    hash: str


@dataclass
class MemorySearchResult:
    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: str = "memory"


# ---------------------------------------------------------------------------
# Utilities (mirrors openclaw/src/memory/internal.ts)
# ---------------------------------------------------------------------------

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_markdown(
    content: str,
    chunk_tokens: int = 400,
    overlap_tokens: int = 80,
) -> list[MemoryChunk]:
    """
    Split markdown content into overlapping chunks.
    Port of openclaw chunkMarkdown() — uses char-based heuristic (4 chars ≈ 1 token).
    """
    lines = content.split("\n")
    if not lines:
        return []

    max_chars = max(32, chunk_tokens * 4)
    overlap_chars = max(0, overlap_tokens * 4)
    chunks: list[MemoryChunk] = []

    current: list[tuple[str, int]] = []  # (line_text, 1-indexed line_no)
    current_chars = 0

    def flush():
        nonlocal current, current_chars
        if not current:
            return
        text = "\n".join(line for line, _ in current)
        start_line = current[0][1]
        end_line = current[-1][1]
        chunks.append(MemoryChunk(
            start_line=start_line,
            end_line=end_line,
            text=text,
            hash=hash_text(text),
        ))

    def carry_overlap():
        nonlocal current, current_chars
        if overlap_chars <= 0 or not current:
            current = []
            current_chars = 0
            return
        kept: list[tuple[str, int]] = []
        acc = 0
        for line_text, line_no in reversed(current):
            acc += len(line_text) + 1
            kept.insert(0, (line_text, line_no))
            if acc >= overlap_chars:
                break
        current = kept
        current_chars = sum(len(t) + 1 for t, _ in kept)

    for i, line in enumerate(lines):
        line_no = i + 1
        line_size = len(line) + 1
        if current_chars + line_size > max_chars and current:
            flush()
            carry_overlap()
        current.append((line, line_no))
        current_chars += line_size

    flush()
    return chunks


# ---------------------------------------------------------------------------
# BM25 simple scorer (no external deps, mirrors openclaw hybrid BM25)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple unicode-aware tokenizer."""
    return [t.lower() for t in re.findall(r"[\w\u0E00-\u0E7F]+", text)]


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    k1: float = 1.5,
    b: float = 0.75,
    avg_dl: float = 100.0,
) -> float:
    """Okapi BM25 score for a single document."""
    if not query_tokens or not doc_tokens:
        return 0.0
    dl = len(doc_tokens)
    tf_map: dict[str, int] = {}
    for tok in doc_tokens:
        tf_map[tok] = tf_map.get(tok, 0) + 1
    score = 0.0
    for qt in query_tokens:
        tf = tf_map.get(qt, 0)
        if tf == 0:
            continue
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / avg_dl)
        score += numerator / denominator
    return score


# ---------------------------------------------------------------------------
# SQLite Memory Index (mirrors openclaw memory-schema.ts)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'memory',
    hash TEXT NOT NULL,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'memory',
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    hash TEXT NOT NULL,
    text TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
"""


# ---------------------------------------------------------------------------
# MemoryManager (per-user)
# ---------------------------------------------------------------------------

class MemoryManager:
    """
    OpenClaw-style memory manager for a single user.

    Manages:
    - MEMORY.md (long-term profile)
    - memory/YYYY-MM-DD.md (daily logs)
    - SQLite chunk index for fast BM25 search
    """

    def __init__(self, user_id: str, data_dir: str = "data/users"):
        self.user_id = user_id
        self.workspace = Path(data_dir) / user_id
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "memory").mkdir(exist_ok=True)

        self._db_path = self.workspace / "index.sqlite"
        self._db = sqlite3.connect(str(self._db_path))
        self._db.executescript(_SCHEMA_SQL)

    # ── File operations ──────────────────────────────────────────────

    @property
    def memory_file(self) -> Path:
        return self.workspace / "MEMORY.md"

    def _daily_log_path(self, date: str | None = None) -> Path:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.workspace / "memory" / f"{date}.md"

    def get_long_term(self) -> str:
        """Read MEMORY.md (user profile / preferences)."""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def get_daily_log(self, date: str | None = None) -> str:
        """Read a daily log. Defaults to today."""
        path = self._daily_log_path(date)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def get_recent_logs(self, days: int = 2) -> str:
        """Read today + yesterday logs (OpenClaw default)."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        parts: list[str] = []
        for i in range(days):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            log = self.get_daily_log(d)
            if log:
                parts.append(f"## {d}\n{log}")
        return "\n\n".join(parts)

    def update_long_term(self, content: str):
        """Overwrite MEMORY.md."""
        self.memory_file.write_text(content, encoding="utf-8")
        self._index_file(self.memory_file, "memory")

    def append_daily_log(self, entry: str, date: str | None = None):
        """Append a line to today's daily log."""
        path = self._daily_log_path(date)
        if not path.exists():
            d = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            path.write_text(f"# {d}\n\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- {entry}\n")
        self._index_file(path, "memory")

    # ── Indexing ─────────────────────────────────────────────────────

    def _index_file(self, file_path: Path, source: str = "memory"):
        """Chunk a file and upsert into SQLite index."""
        if not file_path.exists():
            return
        content = file_path.read_text(encoding="utf-8")
        file_hash = hash_text(content)
        rel_path = str(file_path.relative_to(self.workspace)).replace("\\", "/")
        stat = file_path.stat()

        # Check if file changed
        row = self._db.execute(
            "SELECT hash FROM files WHERE path = ?", (rel_path,)
        ).fetchone()
        if row and row[0] == file_hash:
            return  # no change

        # Update file record
        self._db.execute(
            "INSERT OR REPLACE INTO files (path, source, hash, mtime, size) VALUES (?,?,?,?,?)",
            (rel_path, source, file_hash, stat.st_mtime, stat.st_size),
        )

        # Delete old chunks
        self._db.execute("DELETE FROM chunks WHERE path = ?", (rel_path,))

        # Insert new chunks
        chunks = chunk_markdown(content)
        now = datetime.now(timezone.utc).timestamp()
        for chunk in chunks:
            chunk_id = hash_text(f"{rel_path}:{chunk.start_line}:{chunk.hash}")
            self._db.execute(
                "INSERT OR REPLACE INTO chunks (id, path, source, start_line, end_line, hash, text, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (chunk_id, rel_path, source, chunk.start_line, chunk.end_line, chunk.hash, chunk.text, now),
            )
        self._db.commit()

    def reindex_all(self):
        """Re-index all memory files (MEMORY.md + memory/*.md)."""
        if self.memory_file.exists():
            self._index_file(self.memory_file)
        memory_dir = self.workspace / "memory"
        if memory_dir.exists():
            for md_file in sorted(memory_dir.glob("*.md")):
                self._index_file(md_file)

    # ── Search ───────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> list[MemorySearchResult]:
        """
        BM25 keyword search over all indexed chunks.
        Mirrors openclaw hybrid search (keyword side).
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        rows = self._db.execute(
            "SELECT path, start_line, end_line, text, source FROM chunks"
        ).fetchall()

        if not rows:
            return []

        # Compute avg doc length
        all_doc_lens = [len(_tokenize(row[3])) for row in rows]
        avg_dl = sum(all_doc_lens) / len(all_doc_lens) if all_doc_lens else 100.0

        scored: list[MemorySearchResult] = []
        for row, doc_len in zip(rows, all_doc_lens):
            path, start_line, end_line, text, source = row
            doc_tokens = _tokenize(text)
            score = bm25_score(query_tokens, doc_tokens, avg_dl=avg_dl)
            if score > 0:
                snippet = text[:700] if len(text) > 700 else text
                scored.append(MemorySearchResult(
                    path=path,
                    start_line=start_line,
                    end_line=end_line,
                    score=round(score, 4),
                    snippet=snippet,
                    source=source,
                ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:max_results]

    def build_context(self, query: str, max_results: int = 5) -> str:
        """
        Search memory and return a formatted context string
        ready to inject into LLM prompts.
        """
        results = self.search(query, max_results)
        if not results:
            return ""
        parts = ["[MEMORY CONTEXT]"]
        for r in results:
            parts.append(f"(from {r.path}, lines {r.start_line}-{r.end_line}, score={r.score})")
            parts.append(r.snippet)
            parts.append("")
        return "\n".join(parts)

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self):
        self._db.close()

    def __del__(self):
        try:
            self._db.close()
        except Exception:
            pass
