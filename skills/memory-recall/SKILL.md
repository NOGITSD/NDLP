---
name: memory-recall
description: "Recall stored information about the user from long-term memory"
triggers: ["จำได้ไหม", "remember", "recall", "เคยบอก", "เมื่อวาน", "yesterday", "last time", "ครั้งก่อน", "ฉันชอบ", "ฉันไม่ชอบ"]
---

# Memory Recall Skill

Search MEMORY.md and daily logs to answer user questions about past conversations or stored preferences.

## When to Use
- "จำได้ไหมว่าฉันชอบอะไร?"
- "เมื่อวานคุยเรื่องอะไร?"
- "I told you my cat's name..."

## Actions
- Search memory with the user's query
- Return relevant snippets naturally in conversation
- If nothing found, say so honestly: "ขอโทษนะ จำไม่ได้เรื่องนี้"
