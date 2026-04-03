# Canvas MCP Server

A local MCP server that gives Claude access to your Canvas LMS — courses, assignments, grades, announcements, and to-do items.

## Available Tools

| Tool | Description |
|------|-------------|
| `canvas_list_courses` | List all active enrolled courses |
| `canvas_get_upcoming_assignments` | All assignments due in the next N days across all courses |
| `canvas_list_assignments` | Assignments for a specific course |
| `canvas_get_missing_submissions` | Overdue/missing assignments |
| `canvas_list_announcements` | Recent announcements from instructors |
| `canvas_get_todo` | Canvas to-do list |
| `canvas_get_grades` | Current grades for all courses |

## Setup

### 1. Install Python dependencies

```bash
cd canvas-mcp
pip install -r requirements.txt
```

### 2. Get your Canvas API token

1. Log into Canvas
2. Go to **Account → Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Give it a name (e.g. "Claude MCP") and click **Generate Token**
6. Copy the token — you won't see it again

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
- `CANVAS_API_TOKEN` — the token you just generated
- `CANVAS_BASE_URL` — your school's Canvas URL (e.g. `https://canvas.yourschool.edu`)

### 4. Register with Claude Code (MCP config)

Add this to your Claude MCP configuration (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "canvas": {
      "command": "python",
      "args": ["/absolute/path/to/canvas-mcp/server.py"],
      "env": {
        "CANVAS_API_TOKEN": "your_token_here",
        "CANVAS_BASE_URL": "https://yourschool.instructure.com"
      }
    }
  }
}
```

Replace `/absolute/path/to/canvas-mcp/server.py` with the actual path where you cloned this repo.

> **Note:** You can put the token directly in the `env` block (as shown above) instead of using a `.env` file — whichever you prefer. Never commit either to version control.

## Local Development

Install the development dependencies and run the test suite before pushing changes:

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests cover the shared request helpers, pagination behavior, and user-facing error messages.

## Usage Examples

Once connected, just ask Claude naturally:

- *"What assignments do I have due this week?"*
- *"Am I missing anything?"*
- *"What are my current grades?"*
- *"Any announcements from my professors?"*
- *"Run my morning briefing"* — the `morning-briefing` skill will pull Canvas data automatically

