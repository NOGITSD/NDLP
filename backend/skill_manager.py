"""
OpenClaw-style Skill Manager for Project Jarvis.
Ported from openclaw/skills/ (SKILL.md format).

Each skill is a Markdown file with YAML frontmatter:
---
name: weather
description: "Get weather forecasts"
triggers: ["weather", "temperature", "forecast"]
---
# Weather Skill
...instructions for the LLM...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Skill:
    name: str
    description: str
    triggers: list[str] = field(default_factory=list)
    body: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_skill_md(content: str) -> Skill:
    """Parse a SKILL.md file with YAML frontmatter."""
    # Split frontmatter from body
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return Skill(name="unknown", description="", body=content)

    frontmatter_raw = match.group(1)
    body = match.group(2).strip()

    # Simple YAML-like parser (no pyyaml dependency)
    meta: dict[str, Any] = {}
    for line in frontmatter_raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.startswith("[") and value.endswith("]"):
                # Simple list parse: ["a", "b", "c"]
                items = re.findall(r'"([^"]*)"', value)
                if not items:
                    items = re.findall(r"'([^']*)'", value)
                if not items:
                    items = [v.strip() for v in value.strip("[]").split(",") if v.strip()]
                meta[key] = items
            else:
                meta[key] = value

    return Skill(
        name=meta.get("name", "unknown"),
        description=meta.get("description", ""),
        triggers=meta.get("triggers", []),
        body=body,
        metadata={k: v for k, v in meta.items() if k not in ("name", "description", "triggers")},
    )


class SkillManager:
    """
    Loads SKILL.md files and matches user messages to skills.
    """

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self._load_all()

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for skill_path in sorted(self.skills_dir.rglob("SKILL.md")):
            try:
                content = skill_path.read_text(encoding="utf-8")
                skill = _parse_skill_md(content)
                self.skills[skill.name] = skill
            except Exception:
                pass

    def reload(self):
        self.skills.clear()
        self._load_all()

    def match(self, message: str) -> Skill | None:
        """Find the best matching skill for a user message (trigger keyword match)."""
        lower = message.lower()
        best: Skill | None = None
        best_count = 0
        for skill in self.skills.values():
            count = sum(1 for t in skill.triggers if t.lower() in lower)
            if count > best_count:
                best = skill
                best_count = count
        return best

    def get_skill_context(self, skill_name: str) -> str:
        """Get the full body of a skill for prompt injection."""
        skill = self.skills.get(skill_name)
        if not skill:
            return ""
        return f"[SKILL: {skill.name}]\n{skill.description}\n\n{skill.body}"

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {"name": s.name, "description": s.description}
            for s in self.skills.values()
        ]
