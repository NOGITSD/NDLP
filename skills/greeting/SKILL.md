---
name: greeting
description: "Handle greetings and casual conversation openers"
triggers: ["สวัสดี", "hello", "hi", "หวัดดี", "ดีจ้า", "hey", "good morning", "อรุณสวัสดิ์"]
---

# Greeting Skill

Respond warmly when user greets. Use their name if known from memory.
Adjust tone based on current EVC emotional state.

## Guidelines
- If trust > 0.7: greet like a close friend
- If trust < 0.3: greet politely but maintain distance
- Reference time of day if available
- If daily log shows user was stressed yesterday, ask how they are feeling today
