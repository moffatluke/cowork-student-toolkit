# Cowork Student Toolkit

Tools for students using [Claude Cowork](https://claude.ai) with Canvas LMS and Obsidian. Replaces app-hopping with one AI-powered workflow: Canvas data in Claude, daily briefings, end-of-day wrap-ups, and notes saved straight to your vault.

## What's Included

### Canvas MCP Server (`canvas-mcp/`)

A local [MCP server](https://modelcontextprotocol.io) that connects Claude directly to your Canvas LMS. Once installed, you can ask Claude things like:

- *"What assignments do I have due this week?"*
- *"Am I missing anything?"*
- *"What are my current grades?"*
- *"Any announcements from my professors?"*

**Tools provided:**

| Tool | Description |
|------|-------------|
| `canvas_list_courses` | List all active enrolled courses |
| `canvas_get_upcoming_assignments` | All assignments due in the next N days |
| `canvas_list_assignments` | Assignments for a specific course |
| `canvas_get_missing_submissions` | Overdue/missing assignments |
| `canvas_list_announcements` | Recent instructor announcements |
| `canvas_get_todo` | Canvas to-do list |
| `canvas_get_grades` | Current grades for all courses |

---

### Cowork Skills (`skills/`)

Three skills for the [Claude Cowork](https://claude.ai) desktop app. Skills are instruction files that teach Claude a repeatable workflow — drag and drop to install.

#### `morning-briefing.skill`
Generates a daily HTML dashboard that combines your Google Calendar, Gmail, and Canvas assignments into one clean page. Run it every morning to replace 30 minutes of app-hopping with a 60-second scan.

Output: a self-contained `morning-briefing.html` file, opened automatically in your browser.

#### `wrapup.skill`
End-of-day wrap-up. Audits what Cowork did automatically, asks what you did manually, then generates a dark-mode HTML report with your combined progress, carried-forward items, and a single #1 priority for tomorrow.

Run it manually or set it as a scheduled task at 6pm.

#### `obsidian-daily-note.skill`
Saves the morning briefing and wrap-up to your Obsidian vault as a clean markdown daily note. Each day becomes one file: the briefing creates it in the morning, the wrap-up appends to it in the evening.

---

## Installation

### Canvas MCP Server

**Requirements:** Python 3.8+

**1. Clone and install dependencies**

```bash
git clone https://github.com/moffatluke/cowork-student-toolkit.git
cd cowork-student-toolkit/canvas-mcp
pip install -r requirements.txt
```

**2. Get your Canvas API token**

1. Log into Canvas
2. Go to **Account → Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Name it (e.g. "Claude MCP"), click **Generate Token**, copy it

**3. Create your `.env` file**

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
CANVAS_API_TOKEN=your_token_here
CANVAS_BASE_URL=https://yourschool.instructure.com
```

The server loads this file automatically — your credentials stay out of your Claude config.

**4. Register with Claude**

**Claude Desktop** — add to your MCP config file:
- Windows: `AppData\Roaming\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "canvas": {
      "command": "python",
      "args": ["C:/path/to/cowork-student-toolkit/canvas-mcp/server.py"]
    }
  }
}
```

**Claude Code CLI** — run once in your terminal:

```bash
claude mcp add canvas python /path/to/cowork-student-toolkit/canvas-mcp/server.py
```

Replace the path with wherever you cloned the repo. Restart Claude after saving — you should see the Canvas tools appear in the tool list.

**5. Run the tests (optional)**

```bash
pip install -r requirements-dev.txt
pytest -q
```

The same test suite runs in GitHub Actions on every push.

---

### Cowork Skills

**Requirements:** [Claude Cowork](https://claude.ai) desktop app

1. Download the `.skill` files from the `skills/` folder in this repo
2. Open Claude Cowork
3. Go to **Settings → Skills**
4. Drag and drop the `.skill` files into the skills panel

Once installed:
- Type `/morning-briefing` to run the morning briefing
- Type `/wrapup` to run the end-of-day wrap-up
- The `obsidian-daily-note` skill runs automatically after the other two, or you can trigger it manually

**Note for the Obsidian skill:** When first running `obsidian-daily-note`, Cowork will prompt you to select your vault folder. Select the root of your vault (e.g. `C:\Users\YourName\YourVaultName`). Daily notes will be saved to a `Daily Notes/` subfolder inside it.

---

## Who This Is For

Students who:
- Use Canvas LMS at their school
- Use Claude Cowork for AI-assisted studying and productivity
- Use Obsidian for notes (optional — the Canvas MCP and skills work without it)
- Want their assignments, emails, and schedule in one place without opening five apps

---

## Security Notes

- Your Canvas API token lives only in your local `.env` file, which is excluded from version control via `.gitignore`. Never commit it.
- The MCP server only makes read-only API calls. It cannot submit assignments, post grades, or modify anything in Canvas.
- Token scope: Canvas access tokens grant broad read access to your account. Treat them like passwords — do not share them.

---

## License

MIT
