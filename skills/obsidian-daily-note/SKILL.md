---
name: obsidian-daily-note
description: >
  Saves daily briefing and wrap-up data to your Obsidian vault as a clean markdown daily note.
  Creates a new note each morning with the morning briefing contents, then appends wrap-up data
  in the evening — so each day becomes one complete document in the vault.

  Use this skill whenever the user asks to save to Obsidian, sync their briefing to the vault,
  update their daily note, or when the morning-briefing or wrapup skills finish running.
  Also invoke it directly if the user says anything like "put that in Obsidian", "save to my vault",
  "add this to my daily note", or "update Obsidian".
allowed-tools:
  - Read
  - Write
  - Bash
  - mcp__cowork__request_cowork_directory
---

# Obsidian Daily Note

Save today's data to your Obsidian vault as a clean markdown daily note. Each day gets one file. The morning briefing creates it; the evening wrap-up appends to it.

---

## STEP 1: GET ACCESS TO THE VAULT

Use the `request_cowork_directory` tool to request access to your Obsidian vault folder. When prompted, select the root folder of your vault (e.g. `C:\Users\YourName\YourVaultName`).

Once access is granted, the vault will be available as a mounted directory in your Cowork session.

Create the `Daily Notes` subfolder if it does not exist:
```bash
mkdir -p "VAULT_MOUNT_PATH/Daily Notes"
```

Get today's date:
```bash
date +%Y-%m-%d
```

The daily note lives at: `Daily Notes/YYYY-MM-DD.md`

---

## STEP 2: DETERMINE MODE

Check if a daily note already exists for today:
```bash
ls "VAULT_MOUNT_PATH/Daily Notes/$(date +%Y-%m-%d).md" 2>/dev/null && echo "exists" || echo "new"
```

- **"new"** → you are in **Morning Mode**: create the full note with morning briefing content
- **"exists"** → you are in **Evening Mode**: append the wrap-up section to the existing note

---

## STEP 3A: MORNING MODE — CREATE THE DAILY NOTE

Build the markdown file from the morning briefing data already gathered in this session. Draw from the Canvas, Gmail, and Calendar data that the morning-briefing skill just fetched. If called standalone (not after morning-briefing), pull from the most recent `outputs/morning-briefing-[date].html` file or re-gather the data as needed.

Use this exact template:

```markdown
---
date: YYYY-MM-DD
day: [Full weekday name]
tags: [daily-note, cowork]
---

# [Weekday], [Month Day, Year]

## Morning Briefing

### Today's Focus
1. **[Priority 1]** — [one-line context]
2. **[Priority 2]** — [one-line context]
3. **[Priority 3]** — [one-line context]

### Canvas

**Missing submissions:**
[List items as "- [Assignment] — [Course]" or "- None" if clear]

**Due soon:**
[List items as "- [Assignment] — [Course] — due [date/time]", one per line]

**Announcements:**
[List items as "- [Professor/Course]: [summary]" or "- None" if none]

### Schedule
[List as "- [HH:MM] [Event title] — [location/link if available]", one per line]

### Email
[List as "- [Sender] -> [Subject] — [one-sentence summary]" for urgent]
[Write "- Nothing urgent" if inbox is clear]

### News
[List 3-4 headlines as "- [Headline] ([Source])"]
```

Write this to `Daily Notes/YYYY-MM-DD.md`.

---

## STEP 3B: EVENING MODE — APPEND WRAP-UP

Read the existing daily note, then append the following section at the end. Draw from the wrap-up data gathered in this session (what Cowork did, what the user reported, the synthesis).

Append exactly this:

```markdown

---

## End of Day Wrap-Up

### What Cowork Did
[List as "- [specific item]", one per line]

### What You Did
[List as "- [specific item]", one per line]

### Combined Progress
[2-3 sentences synthesizing both. What moved forward? Where do things stand?]

### Carried Forward
[List as "- [item]", one per line. Only genuine next-day items.]

### Tomorrow's #1 Priority
**[One specific task]**

[One sentence: why this above everything else]

### Reflection
[2-3 sentences. Honest and direct. What worked, what did not, what you would change.]
```

---

## STEP 4: CONFIRM

After writing or appending, confirm to the user:

> "Saved to your Obsidian vault → `Daily Notes/YYYY-MM-DD.md`"

---

## RULES

- **One file per day.** Never create duplicates. Always check before creating.
- **Morning creates, evening appends.** Never overwrite an existing note — only add the wrap-up section at the bottom.
- **Preserve Obsidian-friendly markdown.** Use standard markdown only — no HTML, no raw CSS. Obsidian renders standard `#` headers, `-` lists, `**bold**`, and YAML frontmatter correctly.
- **Be specific.** "Study for HIST 202 exam" beats "study". Pull exact names and times from the data.
- **If data is missing**, note it plainly: `- (no canvas data available)`. Do not invent or pad.
- **Do not re-request vault access** if you already have it in this session. The folder stays mounted.
