---
name: wrapup
description: End-of-day wrap-up for a CS/AI student. Reviews what Claude Cowork did automatically today AND what you did manually, then generates a clean HTML report. Run as a Scheduled Task at 6pm weekdays or trigger manually.
allowed-tools:
  - Read
  - Write
  - Glob
  - Bash
  - WebSearch
---

Run my end-of-day wrap-up.

## WHAT THIS DOES

This is a self-learning end-of-day system built for a computer science student. It does two things:

1. **Audits itself** — Scans what Claude Cowork did automatically today: scheduled tasks that ran, files it created or modified, research it pulled.
2. **Asks what you did** — Asks for a quick brain-dump of what you worked on manually: assignments, coding, studying, reading papers, etc.

Then it combines both into one clean end-of-day picture and saves it as a beautiful dark-mode HTML report you can open in your browser.

---

## HOW IT WORKS

### STEP 1: COWORK'S OWN AUDIT

Before asking the user anything, scan the outputs folder for files created or modified in the last 24 hours.

Run:
```bash
find outputs/ -type f -newer "$(date -d '24 hours ago' '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -v-24H '+%Y-%m-%d %H:%M:%S')" 2>/dev/null | head -60
```

Also check if a scheduled task log exists at `outputs/task_log.json`. If it does, read it and pull today's entries. If it does not exist, create it as an empty array `[]` for future use.

**Build a plain-English list of what Cowork did today**, grouped by category:
- Files generated (reports, dashboards, code files, etc.)
- Research or web searches performed
- Documents or notes created
- Skills created or updated
- Other outputs

If nothing was found, say so honestly: "No automated outputs detected today."

---

### STEP 2: ASK THE USER

After completing the audit, ask ONE question:

> "Here's what I did today: [list Cowork's activity]
>
> Now tell me what YOU did — quick brain dump. Bullet points, half sentences, doesn't matter. What did you work on today? (Assignments, coding, studying, classes, anything)"

Wait for the user's response before continuing.

---

### STEP 3: GENERATE THE WRAP-UP

Combine both sources into this format:

```
## End of Day — [Weekday, Month Day, Year]

### What Cowork Did (Automatically)
- [specific output, e.g. "Generated morning briefing dashboard"]
- [e.g. "Ran a web search on transformer architecture papers"]

### What You Did
- [specific thing from user's brain dump, cleaned up]
- [e.g. "Finished Problem Set 3 for Algorithms"]
- [e.g. "Debugged the data loader for the ML project"]
- [e.g. "Attended Operating Systems lecture, took notes on virtual memory"]

### Combined Progress — What Actually Got Done
[2-3 sentences synthesizing both lists. What moved forward academically and on projects? Where does everything stand right now?]

### Carried Forward
- [unfinished thing that needs action — assignment not done, bug not fixed, concept still unclear]
- [another if needed]

### Tomorrow's #1 Priority
**[One clear, specific thing — e.g. "Submit the neural network lab by 11:59pm"]**

Why this first: [one sentence — urgency, deadline, or impact]

### Reflection
[2-3 sentences. Honest and direct. What clicked today? What was slow or frustrating? What would you do differently?]
```

**Rules:**
- Write in plain English. Short sentences. No jargon.
- "What Cowork Did" should be specific — not "generated content" but the actual file name or task
- "What You Did" should clean up the brain dump without losing the meaning
- Surface any upcoming deadlines in "Carried Forward" if the user mentioned them
- "Tomorrow's #1 Priority" is ONE thing. Force the choice. If there is an assignment due tomorrow, that is it.
- "Reflection" is honest and useful, not cheerful. If today was slow or unproductive, say so.
- Never write "Great job!" or "You crushed it!" — be real and direct

---

### STEP 4: GENERATE THE HTML REPORT

After showing the text wrap-up, generate a self-contained HTML file and save it to:

`outputs/wrapup-[YYYY-MM-DD].html`

Use this template, substituting all `[PLACEHOLDER]` values:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>End of Day — [DATE]</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0a0a0c;
      --surface: #131318;
      --text: #e8e8ed;
      --text-dim: #7a7a8c;
      --text-muted: #4a4a58;
      --border: rgba(255,255,255,0.06);
      --accent: #6366f1;
      --accent-glow: rgba(99,102,241,0.15);
      --green: #22c55e;
      --green-bg: rgba(34,197,94,0.08);
      --yellow: #eab308;
      --yellow-bg: rgba(234,179,8,0.08);
      --blue: #3b82f6;
      --blue-bg: rgba(59,130,246,0.08);
      --orange: #f97316;
      --orange-bg: rgba(249,115,22,0.08);
      --radius: 12px;
      --radius-sm: 8px;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh; }
    .container { max-width: 900px; margin: 0 auto; padding: 48px 24px 80px; }
    .header { margin-bottom: 48px; }
    .date-label { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); letter-spacing: 2px; text-transform: uppercase; font-weight: 500; }
    .pulse-dot { width: 8px; height: 8px; background: var(--accent); border-radius: 50%; animation: pulse 2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    h1 { font-size: 42px; font-weight: 700; letter-spacing: -1.5px; line-height: 1.1; background: linear-gradient(135deg, var(--text) 0%, var(--text-dim) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .subtitle { color: var(--text-dim); font-size: 15px; margin-top: 8px; }
    .section { margin-top: 40px; }
    .section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
    .section-icon { width: 32px; height: 32px; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
    .section-label { font-size: 11px; font-family: 'JetBrains Mono', monospace; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 500; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; }
    .item-list { list-style: none; display: flex; flex-direction: column; gap: 10px; }
    .item { display: flex; align-items: flex-start; gap: 12px; font-size: 15px; color: var(--text); line-height: 1.5; }
    .item-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 8px; flex-shrink: 0; }
    .green .section-icon { background: var(--green-bg); }
    .green .section-label { color: var(--green); }
    .green .item-dot { background: var(--green); }
    .blue .section-icon { background: var(--blue-bg); }
    .blue .section-label { color: var(--blue); }
    .blue .item-dot { background: var(--blue); }
    .orange .section-icon { background: var(--orange-bg); }
    .orange .section-label { color: var(--orange); }
    .orange .item-dot { background: var(--orange); }
    .yellow .section-icon { background: var(--yellow-bg); }
    .yellow .section-label { color: var(--yellow); }
    .yellow .item-dot { background: var(--yellow); }
    .priority-card { background: var(--surface); border: 1px solid rgba(99,102,241,0.3); border-radius: var(--radius); padding: 24px; position: relative; overflow: hidden; }
    .priority-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--accent), transparent); }
    .priority-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; color: var(--accent); margin-bottom: 10px; }
    .priority-task { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; line-height: 1.3; color: var(--text); margin-bottom: 10px; }
    .priority-why { font-size: 14px; color: var(--text-dim); line-height: 1.6; }
    .prose-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; font-size: 15px; color: var(--text-dim); line-height: 1.7; }
    .stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 40px; }
    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; text-align: center; }
    .stat-num { font-size: 28px; font-weight: 700; letter-spacing: -1px; color: var(--text); }
    .stat-label { font-size: 12px; color: var(--text-dim); margin-top: 4px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 1px; }
    .footer { margin-top: 60px; padding-top: 24px; border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
    .footer-text { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); letter-spacing: 1px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <span class="date-label">[DATE_LABEL]</span>
        <div class="pulse-dot"></div>
      </div>
      <h1>End of Day</h1>
      <p class="subtitle">Here's everything that moved forward today — yours and mine.</p>
    </div>

    <div class="stats-row">
      <div class="stat-card"><div class="stat-num">[COWORK_COUNT]</div><div class="stat-label">Cowork outputs</div></div>
      <div class="stat-card"><div class="stat-num">[USER_COUNT]</div><div class="stat-label">Tasks done</div></div>
      <div class="stat-card"><div class="stat-num">[CARRIED_COUNT]</div><div class="stat-label">Carried forward</div></div>
    </div>

    <div class="section green">
      <div class="section-header">
        <div class="section-icon">⚡</div>
        <span class="section-label">What Cowork Did</span>
      </div>
      <div class="card"><ul class="item-list">[COWORK_ITEMS]</ul></div>
    </div>

    <div class="section blue">
      <div class="section-header">
        <div class="section-icon">🧠</div>
        <span class="section-label">What You Did</span>
      </div>
      <div class="card"><ul class="item-list">[USER_ITEMS]</ul></div>
    </div>

    <div class="section orange">
      <div class="section-header">
        <div class="section-icon">📊</div>
        <span class="section-label">Combined Progress</span>
      </div>
      <div class="prose-card"><p>[COMBINED_PROGRESS]</p></div>
    </div>

    <div class="section yellow">
      <div class="section-header">
        <div class="section-icon">→</div>
        <span class="section-label">Carried Forward</span>
      </div>
      <div class="card"><ul class="item-list">[CARRIED_ITEMS]</ul></div>
    </div>

    <div class="section" style="margin-top:40px;">
      <div class="section-header">
        <div class="section-icon" style="background:var(--accent-glow);width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;">01</div>
        <span class="section-label" style="color:var(--accent);font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;">Tomorrow's #1 Priority</span>
      </div>
      <div class="priority-card">
        <div class="priority-label">START HERE TOMORROW</div>
        <div class="priority-task">[PRIORITY_TASK]</div>
        <div class="priority-why">[PRIORITY_WHY]</div>
      </div>
    </div>

    <div class="section" style="margin-top:40px;">
      <div class="section-header">
        <div class="section-icon" style="background:var(--accent-glow);width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;">◆</div>
        <span class="section-label" style="color:var(--accent);font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;">Reflection</span>
      </div>
      <div class="prose-card"><p>[REFLECTION]</p></div>
    </div>

    <div class="footer">
      <span class="footer-text">CLAUDE COWORK — END OF DAY</span>
      <span class="footer-text">[DATE_LABEL]</span>
    </div>
  </div>
</body>
</html>
```

**Fill in every `[PLACEHOLDER]`** with actual content from the wrap-up:

| Placeholder | What to fill in |
|---|---|
| `[DATE]` | Full date string e.g. "March 12, 2026" |
| `[DATE_LABEL]` | Uppercase e.g. "THURSDAY — MARCH 12, 2026" |
| `[COWORK_COUNT]` | Number of things Cowork did |
| `[USER_COUNT]` | Number of things user did |
| `[CARRIED_COUNT]` | Number of things carried forward |
| `[COWORK_ITEMS]` | HTML list items: `<li class="item"><span class="item-dot"></span>[item]</li>` |
| `[USER_ITEMS]` | Same format for user's tasks |
| `[COMBINED_PROGRESS]` | 2-3 sentence synthesis paragraph |
| `[CARRIED_ITEMS]` | Same format for carried-forward items |
| `[PRIORITY_TASK]` | The ONE thing to start tomorrow with |
| `[PRIORITY_WHY]` | One sentence: why this above everything else |
| `[REFLECTION]` | 2-3 sentence honest reflection |

After writing the file, tell the user and provide a link to open it.

---

### STEP 5: UPDATE THE TASK LOG

After every wrap-up, append a record to `outputs/task_log.json`:

```json
{
  "date": "[YYYY-MM-DD]",
  "triggered_by": "scheduled or manual",
  "cowork_outputs": ["list of file paths found"],
  "user_tasks_count": 0,
  "carried_forward_count": 0,
  "priority": "[tomorrow's priority text]",
  "report_path": "outputs/wrapup-[YYYY-MM-DD].html"
}
```

---

## SCHEDULED TASK SETUP

To run this automatically at the end of every weekday:

1. Open your Claude Cowork Project
2. Go to **Scheduled Tasks**
3. Create a new task:
   - **Time:** 6:00 PM (your local time)
   - **Frequency:** Every weekday (Mon–Fri)
   - **Prompt:** `/wrapup`
4. Hit save

---

## VARIATIONS

| Command | What it does |
|---------|-------------|
| `/wrapup` | Standard end-of-day wrap-up with HTML report |
| `/wrapup week` | Weekly version — wraps up Mon–Fri, identifies patterns across the week |
| `/wrapup quick` | Just the priority for tomorrow — no HTML, no reflection, 30 seconds |
