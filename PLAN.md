# PROJECT JARVIS — Full-Stack EVC Chatbot Plan

## สิ่งที่มีแล้ว

```
PROJECT_Jarvis/
├── project_jarvis/          ← EVC Engine (Python, ทำงานแล้ว)
│   ├── config.py            ← ค่าคงที่ทั้งหมด (hormones, W matrix, half-life, etc.)
│   ├── hormones.py          ← HormoneSystem (stimulus, decay, cross-interaction)
│   ├── emotions.py          ← EmotionMapper (W × H → 8 emotions)
│   ├── evc_core.py          ← EVCEngine (orchestrator: hormone → emotion → memory → trust)
│   └── eval_mode.py         ← Eval mode (100-turn simulation + charts)
│
├── frontend/                ← Vite + React 19 (เปล่า, มีแค่ scaffold)
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       └── main.jsx
│
└── Implementing EVC Hormone Model.md  ← บันทึกไอเดีย/สมการ
```

---

## เป้าหมาย

**สร้าง chatbot ที่มีอารมณ์ของตัวเอง** พร้อม deploy ให้กรรมการดูสดได้
- แชทกับ bot ได้จริง (ภาษาไทย + อังกฤษ)
- เห็นฮอร์โมน 8 ตัว + อารมณ์ 8 ตัว เคลื่อนไหว real-time
- bot ตอบตามอารมณ์ปัจจุบัน (ไม่ใช่ reset ทุก turn)
- ใช้ Groq API (เร็ว + ถูก)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Chat UI    │  │  Hormone     │  │  Emotion      │  │
│  │  (messages)  │  │  Bar Chart   │  │  Radar/Blend  │  │
│  │              │  │  (8 bars)    │  │  (8 emotions) │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│         │     ┌───────────┴───────────┐       │          │
│         │     │    Trust Meter        │       │          │
│         │     └───────────────────────┘       │          │
│         └─────────────────┬───────────────────┘          │
│                           │                              │
│                    POST /api/chat                         │
│                    GET  /api/state                        │
└───────────────────────────┼──────────────────────────────┘
                            │
┌───────────────────────────┼──────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  /api/chat (POST)                    │ │
│  │                                                     │ │
│  │  1. รับ message จาก user                             │ │
│  │  2. เรียก Groq 8B → วิเคราะห์ S, D, C, user_emotion │ │
│  │  3. EVC Engine → คำนวณ H[8], E[8], Trust, Memory    │ │
│  │  4. สร้าง system prompt + bot emotion state          │ │
│  │  5. เรียก Groq Large → สร้างคำตอบตามอารมณ์           │ │
│  │  6. return { response, hormones, emotions, trust }   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  EVC Engine  │  │  Groq Bridge │  │  Session      │  │
│  │  (existing)  │  │  (new)       │  │  Manager      │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## File Structure (สิ่งที่ต้องสร้างใหม่)

```
PROJECT_Jarvis/
├── backend/                     ← NEW: FastAPI server
│   ├── main.py                  ← FastAPI app + CORS + routes
│   ├── groq_bridge.py           ← Groq API wrapper (8B analyze + Large chat)
│   ├── session_manager.py       ← Per-session EVC state (in-memory dict)
│   ├── prompts.py               ← System prompts สำหรับ 8B analyzer + Large chatbot
│   ├── requirements.txt         ← fastapi, uvicorn, groq, numpy
│   └── .env.example             ← GROQ_API_KEY=xxx
│
├── project_jarvis/              ← EXISTING: EVC Engine (ย้ายมาใช้ใน backend)
│   ├── config.py
│   ├── hormones.py
│   ├── emotions.py
│   └── evc_core.py
│
├── frontend/                    ← UPDATE: React UI
│   ├── src/
│   │   ├── App.jsx              ← Main layout (Chat + Dashboard)
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx    ← ส่ง/รับข้อความ
│   │   │   ├── HormoneChart.jsx ← Bar chart 8 ฮอร์โมน (animated)
│   │   │   ├── EmotionRadar.jsx ← Radar chart / blend display
│   │   │   ├── TrustMeter.jsx   ← Trust gauge
│   │   │   └── MessageBubble.jsx← Chat bubble + emotion indicator
│   │   ├── hooks/
│   │   │   └── useChat.js       ← API call logic + state
│   │   └── styles/
│   │       └── globals.css      ← Tailwind / custom styles
│   └── package.json             ← + tailwindcss, recharts, lucide-react
│
└── PLAN.md                      ← THIS FILE
```

---

## API Endpoints

### `POST /api/chat`
```json
// Request
{
  "session_id": "abc123",
  "message": "สวัสดีครับ วันนี้เหนื่อยมาก"
}

// Response
{
  "response": "สวัสดีค่ะ เหนื่อยมากเหรอ พักผ่อนบ้างนะ...",
  "user_emotion": "tired/stressed",
  "bot_state": {
    "hormones": {
      "Dopamine": 0.35, "Serotonin": 0.55, "Oxytocin": 0.40,
      "Endorphin": 0.30, "Cortisol": 0.45, "Adrenaline": 0.20,
      "GABA": 0.50, "Norepinephrine": 0.25
    },
    "emotions": {
      "Joy": 0.15, "Serenity": 0.30, "Love": 0.20,
      "Excitement": 0.05, "Sadness": 0.10, "Fear": 0.05,
      "Anger": 0.05, "Surprise": 0.10
    },
    "dominant_emotion": "Serenity",
    "emotion_blend": "Serenity(0.30) + Love(0.20) + Joy(0.15)",
    "trust": 0.65,
    "turn": 5
  }
}
```

### `GET /api/state?session_id=abc123`
```json
// Response — same as bot_state above (สำหรับ polling/refresh)
```

### `POST /api/reset`
```json
// Request
{ "session_id": "abc123" }
// Response
{ "status": "ok", "message": "Session reset" }
```

---

## Groq API Strategy

### Model 1: Analyzer (8B) — ถูก + เร็ว
- **Model**: `llama-3.1-8b-instant`
- **หน้าที่**: วิเคราะห์ข้อความ user → ให้ค่า S, D, C + user_emotion
- **Prompt**: structured, ให้ตอบ JSON เท่านั้น
- **Token cost**: ต่ำมาก (~100 tokens/turn)

### Model 2: Conversationalist (Large) — คุณภาพสูง
- **Model**: `llama-3.3-70b-versatile` หรือ `mixtral-8x7b-32768`
- **หน้าที่**: รับ user message + bot emotion state → สร้างคำตอบ
- **Prompt**: personality prompt + EVC state injection
- **Token cost**: ปานกลาง (~300-500 tokens/turn)

### Flow per turn:
```
User message
    │
    ▼
[Groq 8B] → { S: 0.2, D: 0.6, C: 1.1, user_emotion: "frustrated" }
    │
    ▼
[EVC Engine] → H[8], E[8], trust, memory (pure math, 0 cost)
    │
    ▼
[Groq Large] ← system prompt includes:
    │           "Bot feels: Sadness(0.25) + Fear(0.20) + Serenity(0.15)"
    │           "User seems: frustrated"
    │           "Trust level: 0.6 (moderate)"
    │           "Respond with empathy, gentle tone..."
    ▼
Response → sent to frontend with full state
```

---

## Frontend Layout (สำหรับ committee demo)

```
┌────────────────────────────────────────────────────────────┐
│  🧠 Project Jarvis — EVC Emotional Chatbot                  │
├────────────────────────────────┬───────────────────────────┤
│                                │                           │
│   💬 CHAT                      │  📊 EVC DASHBOARD          │
│                                │                           │
│   ┌──────────────────────┐     │  ┌─────────────────────┐  │
│   │ Bot: สวัสดีค่ะ!       │     │  │ HORMONES (8 bars)   │  │
│   │      [Joy 😊]         │     │  │ ██████ Dopamine     │  │
│   └──────────────────────┘     │  │ ████   Serotonin    │  │
│                                │  │ ███    Oxytocin     │  │
│   ┌──────────────────────┐     │  │ █████  Endorphin    │  │
│   │ User: วันนี้เหนื่อยมาก │     │  │ ███████ Cortisol   │  │
│   └──────────────────────┘     │  │ ██     Adrenaline   │  │
│                                │  │ ████   GABA         │  │
│   ┌──────────────────────┐     │  │ ███    Norepineph.  │  │
│   │ Bot: พักบ้างนะ...     │     │  └─────────────────────┘  │
│   │      [Serenity 😌]    │     │                           │
│   └──────────────────────┘     │  ┌─────────────────────┐  │
│                                │  │ EMOTIONS (blend)     │  │
│                                │  │ 😌 Serenity  30%     │  │
│                                │  │ 💕 Love      20%     │  │
│                                │  │ 😊 Joy       15%     │  │
│                                │  └─────────────────────┘  │
│                                │                           │
│                                │  ┌─────────────────────┐  │
│                                │  │ TRUST ████████░░ 65% │  │
│                                │  └─────────────────────┘  │
│                                │                           │
│   ┌──────────────────────────┐ │  Turn: 5                  │
│   │ พิมพ์ข้อความ...     [Send]│ │  Dominant: Serenity      │
│   └──────────────────────────┘ │                           │
├────────────────────────────────┴───────────────────────────┤
│  Status: Connected │ Model: llama-3.3-70b │ Latency: 320ms │
└────────────────────────────────────────────────────────────┘
```

---

## Dependencies ที่ต้องติดตั้ง

### Backend (Python)
```
fastapi
uvicorn[standard]
groq
numpy
python-dotenv
pydantic
```

### Frontend (npm — เพิ่มจากที่มี)
```
tailwindcss @tailwindcss/vite
recharts                    ← สำหรับ hormone/emotion charts
lucide-react                ← icons
```

---

## Deployment Strategy

### Option A: แยก deploy (แนะนำสำหรับ demo)
- **Frontend** → Netlify (free, ง่าย, เร็ว)
- **Backend** → Railway หรือ Render (free tier, รัน Python ได้)
- **Groq API** → ใช้ API key ของคุณ (เก็บใน env ของ Railway)

### Option B: รวมเป็น 1 (ง่ายกว่าแต่ช้ากว่า)
- FastAPI serve ทั้ง API + static React build
- Deploy ทั้งหมดบน Railway

### สำหรับ demo กรรมการ:
- ใช้ **Option A** — แยก deploy
- Frontend บน Netlify → มี URL สวยๆ ให้กรรมการเปิด
- Backend บน Railway → ฟรี + มี env variables สำหรับ API key

---

## ลำดับการ Implement (ขั้นตอน)

### Phase 1: Backend API (ทำก่อน)
1. สร้าง `backend/` folder + `requirements.txt`
2. เขียน `groq_bridge.py` — Groq API wrapper (8B + Large)
3. เขียน `prompts.py` — system prompts ทั้ง 2 models
4. เขียน `session_manager.py` — จัดการ EVC state per session
5. เขียน `main.py` — FastAPI app + endpoints
6. ทดสอบ backend ด้วย curl / Postman

### Phase 2: Frontend UI (ทำต่อ)
7. ติดตั้ง tailwindcss + recharts + lucide-react
8. สร้าง ChatPanel component
9. สร้าง HormoneChart component (animated bars)
10. สร้าง EmotionRadar component
11. สร้าง TrustMeter component
12. ประกอบทั้งหมดใน App.jsx
13. เชื่อม frontend → backend API

### Phase 3: Polish + Deploy
14. ทดสอบ end-to-end (พิมพ์ข้อความ → เห็นอารมณ์เปลี่ยน)
15. ปรับ UI/UX ให้สวยสำหรับ demo
16. Deploy backend → Railway
17. Deploy frontend → Netlify
18. ทดสอบ production URL

---

## Memory Layer (OpenClaw-Style)

### ทำไมต้องมี Memory?

EVC Engine จำได้แค่ **hormone state** (ตัวเลข) แต่จำไม่ได้ว่า:
- user ชื่ออะไร ชอบอะไร
- เคยคุยเรื่องอะไรไปแล้ว
- user มีนิสัยพูดแบบไหน
- มีนัด/งานอะไรค้างอยู่

**OpenClaw** แก้ปัญหานี้ด้วย **Markdown-based memory + vector search**
เราจะ implement แนวเดียวกันใน Python ให้ทำงานร่วมกับ FastAPI + EVC Engine

---

### Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY SYSTEM                             │
│                                                              │
│  ┌───────────────────────┐  ┌────────────────────────────┐  │
│  │  Long-Term Memory     │  │  Conversation Memory       │  │
│  │  (MEMORY.md per user) │  │  (daily logs per user)     │  │
│  │                       │  │                            │  │
│  │  - ชื่อ, อายุ, งาน     │  │  - memory/2026-02-17.md   │  │
│  │  - ชอบ/ไม่ชอบ         │  │  - memory/2026-02-18.md   │  │
│  │  - นิสัย, คำพูดติดปาก  │  │  - บทสนทนาย่อ per day    │  │
│  │  - เป้าหมายชีวิต       │  │  - สิ่งสำคัญที่เกิดขึ้น     │  │
│  │  - ข้อมูลถาวร         │  │  - context ล่าสุด          │  │
│  └───────────┬───────────┘  └──────────┬─────────────────┘  │
│              │                          │                    │
│              ▼                          ▼                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Vector Index (SQLite + Embeddings)       │   │
│  │  - Chunk memory files (~400 tokens each)              │   │
│  │  - Embed via Groq/local model                         │   │
│  │  - Semantic search: "user ชอบกินอะไร?" → relevant chunks│  │
│  └──────────────────────────────────────────────────────┘   │
│              │                                               │
│              ▼                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              EVC State (per user)                     │   │
│  │  - H[8] hormone levels                               │   │
│  │  - E[8] emotion scores                                │   │
│  │  - Trust level                                        │   │
│  │  - Emotional memory M[8]                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

### Memory File Structure (per user)

```
data/
├── users/
│   ├── user_abc123/
│   │   ├── MEMORY.md              ← Long-term: preferences, facts, personality
│   │   ├── memory/
│   │   │   ├── 2026-02-17.md      ← Daily log
│   │   │   ├── 2026-02-18.md
│   │   │   └── ...
│   │   ├── evc_state.json         ← H[8], E[8], Trust, M[8], turn count
│   │   └── index.sqlite           ← Vector index for this user's memory
│   │
│   ├── user_xyz789/
│   │   ├── MEMORY.md
│   │   ├── memory/
│   │   ├── evc_state.json
│   │   └── index.sqlite
│   └── ...
```

---

### MEMORY.md ตัวอย่าง (เขียนโดย bot เอง)

```markdown
# User Profile

## Basic Info
- ชื่อ: พี่เจ (เรียกตัวเองว่า "ผม")
- อายุ: 28
- อาชีพ: นักพัฒนาซอฟต์แวร์
- บริษัท: TechCorp

## Preferences
- ชอบ: กาแฟดำ, อาหารญี่ปุ่น, เพลง Lo-fi
- ไม่ชอบ: ประชุมยาว, อาหารเผ็ดมาก
- สไตล์สื่อสาร: พูดตรง ชอบคำตอบกระชับ ไม่ต้องอ้อมค้อม

## Important Notes
- มีแมว 2 ตัว ชื่อมิกะ กับ โมจิ
- กำลังทำโปรเจค AI chatbot (Project Jarvis)
- ชอบเวลาบอทมีอารมณ์ร่วม ไม่ชอบบอทที่เย็นชา

## Goals
- ส่ง thesis ภายในเดือนมีนาคม
- ออกกำลังกาย 3 ครั้ง/สัปดาห์
```

---

### Daily Log ตัวอย่าง (memory/2026-02-17.md)

```markdown
# 2026-02-17

## Summary
- พี่เจเข้ามาคุยตอนบ่าย อารมณ์ดี ชมบอทว่าเก่ง
- ถามเรื่องตารางประชุมพรุ่งนี้
- บ่นว่าเหนื่อยจากประชุม 3 รอบ

## Key Events
- 14:30 — เริ่มสนทนา, อารมณ์ดี (Joy dominant)
- 15:00 — ถามเรื่องงาน, เริ่มเครียดเล็กน้อย (Cortisol ↑)
- 15:20 — ชมบอท, Dopamine spike
- 15:45 — บอกว่าจะไปพักแล้ว

## To Remember
- พรุ่งนี้มีประชุม 10:00 กับทีม Backend
- อยากให้บอทเตือนเรื่องออกกำลังกาย
```

---

### Flow: Memory ทำงานยังไงในแต่ละ turn

```
User message: "วันนี้เหนื่อยมาก ประชุม 4 รอบ"
    │
    ▼
[1. Memory Search] ← ค้นหา relevant context จาก MEMORY.md + daily logs
    │   query: "เหนื่อย ประชุม"
    │   results: "user ไม่ชอบประชุมยาว", "เมื่อวานก็ประชุม 3 รอบ"
    │
    ▼
[2. Groq 8B Analyzer] ← ส่ง message + memory context
    │   → { S: 0.05, D: 0.55, C: 1.2, user_emotion: "exhausted" }
    │   (C สูงขึ้นเพราะ memory บอกว่า user ไม่ชอบประชุม = กระทบมากขึ้น)
    │
    ▼
[3. EVC Engine] → H[8], E[8], Trust
    │
    ▼
[4. Groq Large] ← system prompt includes:
    │   - bot emotion state
    │   - memory context: "user ชื่อพี่เจ, ไม่ชอบประชุมยาว, เมื่อวานก็เหนื่อย"
    │   - personality: "ตอบกระชับ อย่าอ้อมค้อม"
    │
    ▼
[5. Response]: "พี่เจ... ประชุม 4 รอบเลยเหรอ เมื่อวานก็ 3 รอบ
               หนักมากเลยนะช่วงนี้ พักก่อนนะครับ อย่าลืมยืดเส้นด้วย"
    │
    ▼
[6. Memory Write] ← bot ตัดสินใจว่าจะจดอะไร
    │   → daily log: "2026-02-18: ประชุม 4 รอบ, เหนื่อยมาก, Cortisol สูง"
    │   → MEMORY.md: (ไม่แก้ — ไม่มี fact ใหม่ที่ถาวร)
```

---

### Memory Operations (Python)

```python
# backend/memory_manager.py

class MemoryManager:
    """OpenClaw-style memory for per-user personalization."""

    def __init__(self, user_id: str, data_dir: str = "data/users"):
        ...

    # ── Read ──
    def get_long_term(self) -> str:
        """Read MEMORY.md — user profile, preferences, facts."""

    def get_daily_log(self, date: str = None) -> str:
        """Read daily log (default: today + yesterday)."""

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search across all memory files.
        Returns: [{text, file, score}, ...]"""

    # ── Write ──
    def update_long_term(self, section: str, content: str):
        """Update a section in MEMORY.md (e.g. preferences)."""

    def append_daily_log(self, entry: str):
        """Append to today's daily log."""

    def auto_extract_facts(self, message: str, response: str) -> list[str]:
        """Use LLM to extract durable facts from conversation.
        e.g. 'user mentioned they have a cat named Mika'"""

    # ── Index ──
    def reindex(self):
        """Re-chunk and re-embed all memory files."""
```

---

### Embedding Strategy สำหรับ Vector Search

| Option | วิธี | ข้อดี | ข้อเสีย |
|--------|------|-------|---------|
| **A: Groq Embeddings** | ใช้ Groq API สร้าง embeddings | ง่าย, ไม่ต้องติดตั้งอะไร | เสีย API call ต่อ search |
| **B: Local (sentence-transformers)** | ใช้ `all-MiniLM-L6-v2` local | ฟรี, เร็ว, ไม่ต้อง API | ต้อง install torch (~2GB) |
| **C: Simple keyword (BM25)** | ใช้ text search แบบ TF-IDF | เบามาก, 0 dependency | ไม่ semantic |

**แนะนำ: Option C สำหรับ MVP → Option B สำหรับ production**
- Demo กรรมการ: BM25 เพียงพอ + เบา + deploy ง่าย
- ถ้าอยากเทพ: เพิ่ม sentence-transformers ทีหลัง

---

### Updated Architecture (เพิ่ม Memory Layer)

```
User message
    │
    ▼
[Memory Search] → relevant context from MEMORY.md + daily logs
    │
    ├──────────────────────┐
    ▼                      ▼
[Groq 8B]              [Context Builder]
  S, D, C                memory + user profile
    │                      │
    ▼                      │
[EVC Engine]               │
  H[8], E[8]              │
    │                      │
    ├──────────────────────┘
    ▼
[Groq Large] ← message + emotion + memory context
    │
    ├─→ Response to user
    │
    ▼
[Memory Writer] → append daily log + extract new facts
```

---

### Updated File Structure

```
PROJECT_Jarvis/
├── backend/
│   ├── main.py                  ← FastAPI app
│   ├── groq_bridge.py           ← Groq API (8B + Large)
│   ├── memory_manager.py        ← NEW: OpenClaw-style memory (read/write/search)
│   ├── memory_indexer.py         ← NEW: BM25/vector indexing
│   ├── session_manager.py       ← EVC state + memory per user
│   ├── prompts.py               ← System prompts (includes memory context)
│   ├── requirements.txt         ← + rank-bm25 (or sentence-transformers)
│   └── .env.example
│
├── data/                        ← NEW: persistent user data
│   └── users/
│       └── {user_id}/
│           ├── MEMORY.md
│           ├── memory/
│           │   └── YYYY-MM-DD.md
│           ├── evc_state.json
│           └── index.json       ← BM25 index cache
│
├── project_jarvis/              ← EVC Engine (existing)
├── frontend/                    ← React UI
└── PLAN.md
```

---

### Updated Implementation Phases

### Phase 1: Backend API (ทำก่อน)
1. สร้าง `backend/` folder + `requirements.txt`
2. เขียน `groq_bridge.py` — Groq API wrapper
3. เขียน `prompts.py` — system prompts
4. เขียน `session_manager.py` — EVC state per session
5. เขียน `main.py` — FastAPI app + endpoints
6. ทดสอบ backend ด้วย curl

### Phase 1.5: Memory Layer (หลัง backend ทำงาน)
7. เขียน `memory_manager.py` — read/write MEMORY.md + daily logs
8. เขียน `memory_indexer.py` — BM25 search over memory chunks
9. เชื่อม memory → prompts.py (inject context เข้า LLM prompt)
10. เขียน auto-extract logic (LLM ดึง facts จากบทสนทนา)
11. ทดสอบ: คุย 10 turns → ดูว่า MEMORY.md + daily log ถูกเขียนถูกต้อง

### Phase 2: Frontend UI
12. ติดตั้ง tailwindcss + recharts + lucide-react
13. สร้าง ChatPanel, HormoneChart, EmotionRadar, TrustMeter
14. ประกอบใน App.jsx + เชื่อม API
15. (Optional) เพิ่ม Memory Panel — ให้ user เห็นว่าบอทจำอะไรได้

### Phase 3: Polish + Deploy
16. End-to-end test (local) ผ่าน Docker Compose (`backend` + `frontend` + shared network)
17. สร้าง `Dockerfile` สำหรับ backend (FastAPI + uvicorn) และ frontend (React + Nginx)
18. สร้าง `docker-compose.yml` สำหรับ dev/staging และตั้งค่า env (`GROQ_API_KEY`, API URLs)
19. Build + tag images (`jarvis-backend`, `jarvis-frontend`) แล้ว push ไป container registry (เช่น GHCR/Docker Hub)
20. Deploy แบบ container บน target platform (Railway/Render/Fly.io/Kubernetes) โดยดึง image จาก registry
21. ทดสอบ production + healthcheck + rollback plan (เก็บ image tag ก่อนหน้าไว้เสมอ)

---

## Data + Identity Architecture (WebApp + LINE + Discord)

### เป้าหมาย

ให้ผู้ใช้ 1 คนมี "ตัวตนเดียว" (global identity) และคุยกับ AI ได้ข้ามแพลตฟอร์มโดย:
- login ได้ด้วย Email/Password หรือ Google
- link บัญชี LINE และ Discord เข้ากับ user เดียวกัน
- EVC state + memory ใช้ร่วมกันทุกช่องทาง

---

### Core Principle: 1 User = 1 Assistant Brain

```
user_id (global)
   ├─ web account (email/google)
   ├─ line account (line_user_id)
   ├─ discord account (discord_user_id)
   ├─ evc_state (H[8], E[8], trust, memory vector)
   └─ long-term memory + daily logs
```

ทุกข้อความจากทุก platform จะถูก map เข้า `user_id` เดียวกันก่อนคำนวณ EVC

---

### Recommended Database

- **PostgreSQL**: identity, auth, account linking, sessions, message metadata
- **Object Storage / Volume**: เก็บไฟล์ memory `.md` (OpenClaw-style)
- **Optional pgvector**: semantic search memory จาก DB โดยตรง

> MVP แนะนำ: PostgreSQL + เก็บ `.md` ใน disk/volume ก่อน แล้วค่อยเพิ่ม pgvector

---

### Schema (MVP)

#### 1) users
- `id` (uuid, pk)
- `email` (unique, nullable)
- `password_hash` (nullable ถ้า login ด้วย Google อย่างเดียว)
- `display_name`
- `created_at`, `updated_at`

#### 2) oauth_accounts
- `id` (uuid, pk)
- `user_id` (fk -> users.id)
- `provider` (`google`)
- `provider_user_id` (unique)
- `access_token_encrypted` (optional)
- `created_at`

#### 3) platform_accounts
- `id` (uuid, pk)
- `user_id` (fk -> users.id)
- `platform` (`web`, `line`, `discord`)
- `platform_user_id` (เช่น line userId / discord user id)
- `is_primary` (bool)
- `created_at`
- unique (`platform`, `platform_user_id`)

#### 4) assistant_state
- `user_id` (pk, fk -> users.id)
- `evc_state_json` (H, E, trust, turn, memory vectors)
- `last_active_at`

#### 5) conversations
- `id` (uuid, pk)
- `user_id` (fk)
- `platform` (`web`, `line`, `discord`)
- `channel_id` (line room/group, discord channel)
- `created_at`

#### 6) messages
- `id` (uuid, pk)
- `conversation_id` (fk)
- `user_id` (fk)
- `role` (`user`, `assistant`, `system`)
- `content`
- `emotion_snapshot_json` (optional)
- `created_at`

#### 7) memory_files
- `id` (uuid, pk)
- `user_id` (fk)
- `file_type` (`long_term`, `daily_log`)
- `file_path` (เช่น `data/users/{user_id}/MEMORY.md`)
- `file_date` (nullable, ใช้กับ daily log)
- `checksum`
- `updated_at`

#### 8) memory_chunks (ถ้าจะ search ใน DB)
- `id` (uuid, pk)
- `user_id` (fk)
- `memory_file_id` (fk)
- `chunk_text`
- `embedding` (vector, optional)
- `bm25_tokens` (optional)
- `created_at`

---

### Account Linking Flow (สำคัญมาก)

#### A) Web Login
1. ผู้ใช้สมัคร/ล็อกอินด้วย email+password หรือ Google
2. backend ออก JWT + refresh token
3. สร้าง `users.id` เป็น global identity

#### B) Link LINE
1. ผู้ใช้กด "เชื่อม LINE" ใน web
2. backend สร้าง `link_code` (one-time, หมดอายุเร็ว)
3. ผู้ใช้ส่ง code นี้ให้ LINE bot
4. backend map `line_user_id` -> `users.id` ใน `platform_accounts`

#### C) Link Discord
1. ผู้ใช้กด "เชื่อม Discord" ใน web
2. OAuth2 Discord หรือ link code ผ่าน bot command
3. map `discord_user_id` -> `users.id`

หลัง link สำเร็จ: คุยจาก platform ไหนก็ใช้ state เดียวกัน

---

### Unified Message Pipeline (Cross-Platform)

```
LINE webhook / Discord event / Web chat
        |
        v
[Identity Resolver]
  - หา user_id จาก platform_accounts
        |
        v
[Memory Search]
  - MEMORY.md + daily log (+ vector/BM25)
        |
        v
[Groq Analyzer 8B] -> S, D, C, user emotion
        |
        v
[EVC Engine] -> update hormones/emotions/trust
        |
        v
[Groq Chat Model] -> response with persona + memory context
        |
        +--> save message
        +--> update assistant_state
        +--> append memory daily log
```

---

### OpenClaw Memory in Database (Hybrid Model)

แนะนำให้ใช้แบบ Hybrid:

1. **Source of truth = Markdown files**
   - `MEMORY.md`
   - `memory/YYYY-MM-DD.md`

2. **DB index metadata**
   - เก็บ path, checksum, updated_at ใน `memory_files`
   - ถ้าจะ query เร็ว ค่อยแตก chunk ลง `memory_chunks`

3. **Indexer worker**
   - monitor file changes
   - re-chunk + reindex เฉพาะไฟล์ที่เปลี่ยน

ข้อดี: ได้ความยืดหยุ่นแบบ OpenClaw + query/sync ง่ายใน production

---

### Deployment Notes (Container + Multi-platform)

- services แนะนำใน `docker-compose.yml`
  - `api` (FastAPI)
  - `worker` (memory indexing + async jobs)
  - `postgres`
  - `redis` (queue/cache, optional)
  - `frontend`
- ต้องตั้ง webhook URL สำหรับ LINE/Discord ให้ชี้เข้า API container
- secrets (`GROQ_API_KEY`, `GOOGLE_CLIENT_SECRET`, `LINE_CHANNEL_SECRET`, `DISCORD_BOT_TOKEN`) เก็บใน env/secret manager เท่านั้น

---

## คำถามที่ต้องตัดสินใจก่อน Implement

1. **Groq model สำหรับ chat**: `llama-3.3-70b-versatile` หรือ `mixtral-8x7b-32768`?
2. **ภาษาของ bot**: ตอบภาษาไทยเท่านั้น หรือ ไทย+อังกฤษ?
3. **Bot personality**: มีชื่อ/บุคลิกเฉพาะไหม? (เช่น "Jarvis เลขาใจดี")
4. **Deploy platform**: Netlify + Railway โอเคไหม? หรือมี platform อื่นที่ต้องใช้?
