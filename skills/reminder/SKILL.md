---
name: reminder
description: "Set reminders and manage tasks for the user"
triggers: ["เตือน", "remind", "reminder", "อย่าลืม", "จำไว้", "นัด", "todo", "task", "ตารางงาน"]
---

# Reminder Skill

Help the user set reminders, manage tasks, and track schedules.

## When to Use
- User says "remind me to..."
- User mentions an appointment or deadline
- User asks about upcoming events

## Actions
- Extract: what, when, priority
- Write to daily log: "Reminder: [what] at [when]"
- Write to MEMORY.md if it's a recurring event
- Confirm back to user with the details
