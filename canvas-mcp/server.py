#!/usr/bin/env python3
"""
Canvas LMS MCP Server

Provides tools for students to interact with the Canvas LMS API:
courses, assignments, announcements, grades, todo items, and missing submissions.
"""

import os
import json
from typing import Optional, List, Any
from datetime import datetime, timezone
import httpx
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
# Server initialization
# ─────────────────────────────────────────────

mcp = FastMCP("canvas_mcp")

CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "").rstrip("/")
CANVAS_API_TOKEN = os.environ.get("CANVAS_API_TOKEN", "")


# ─────────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────────

def _headers() -> dict:
    """Return auth headers for Canvas API requests."""
    return {"Authorization": f"Bearer {CANVAS_API_TOKEN}"}


def _check_config() -> Optional[str]:
    """Return an error string if env vars are missing, else None."""
    if not CANVAS_API_TOKEN:
        return "Error: CANVAS_API_TOKEN environment variable is not set."
    if not CANVAS_BASE_URL:
        return "Error: CANVAS_BASE_URL environment variable is not set (e.g. https://yourschool.instructure.com)."
    return None


async def _get(endpoint: str, params: Optional[dict] = None) -> Any:
    """
    GET from Canvas API with automatic Link-header pagination.
    Returns a list for list endpoints, or a dict for single-object endpoints.
    """
    url = f"{CANVAS_BASE_URL}/api/v1/{endpoint.lstrip('/')}"
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            response = await client.get(url, headers=_headers(), params=params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                results.extend(data)
            else:
                return data

            # Follow Link header for next page
            next_url = None
            link_header = response.headers.get("Link", "")
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break

            url = next_url
            params = None  # Already encoded in next_url

    return results


def _handle_error(e: Exception) -> str:
    """Return a human-readable, actionable error message."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error: Unauthorized. Your CANVAS_API_TOKEN may be expired or invalid — regenerate it in Canvas under Account → Settings → New Access Token."
        elif code == 403:
            return "Error: Permission denied. You may not have access to this resource."
        elif code == 404:
            return "Error: Not found. Double-check the course ID — use canvas_list_courses to find valid IDs."
        elif code == 429:
            return "Error: Rate limit exceeded. Wait a moment and try again."
        return f"Error: Canvas API returned HTTP {code}."
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Check your network connection."
    elif isinstance(e, ValueError):
        return f"Error: {e}"
    return f"Error: {type(e).__name__}: {e}"


def _fmt_date(date_str: Optional[str]) -> str:
    """Format an ISO date string into a human-readable UTC form."""
    if not date_str:
        return "No due date"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        hour = dt.strftime("%I").lstrip("0") or "0"
        return f"{dt.strftime('%a %b')} {dt.day}, {dt.year} at {hour}:{dt.strftime('%M')} {dt.strftime('%p')} UTC"
    except Exception:
        return date_str


def _days_until(date_str: Optional[str]) -> Optional[int]:
    """Return integer days until a due date (negative = past due)."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        delta = dt - datetime.now(timezone.utc)
        return delta.days
    except Exception:
        return None


def _urgency_label(days: Optional[int]) -> str:
    """Return a short urgency label based on days until due."""
    if days is None:
        return ""
    if days < 0:
        return " [OVERDUE]"
    if days == 0:
        return " [DUE TODAY]"
    if days == 1:
        return " [DUE TOMORROW]"
    if days <= 3:
        return f" [DUE IN {days} DAYS]"
    return ""


# ─────────────────────────────────────────────
# Pydantic input models
# ─────────────────────────────────────────────

class ListCoursesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    include_concluded: bool = Field(
        default=False,
        description="If true, include concluded/past courses. Default: only active courses."
    )


class ListAssignmentsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    course_id: str = Field(
        ...,
        description="Canvas course ID. Use canvas_list_courses to find IDs.",
        min_length=1
    )
    upcoming_only: bool = Field(
        default=False,
        description="If true, only return assignments with future due dates."
    )
    include_submitted: bool = Field(
        default=True,
        description="If false, hide assignments already submitted."
    )


class UpcomingAssignmentsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    days_ahead: int = Field(
        default=14,
        description="How many days ahead to look for upcoming assignments. Default: 14.",
        ge=1,
        le=90
    )
    include_no_due_date: bool = Field(
        default=False,
        description="If true, also include assignments with no due date set."
    )


class AnnouncementsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    days_back: int = Field(
        default=7,
        description="How many days back to fetch announcements. Default: 7.",
        ge=1,
        le=60
    )


class CourseGradesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    course_id: Optional[str] = Field(
        default=None,
        description="Specific course ID. If omitted, returns grades for all active courses."
    )


# ─────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────

@mcp.tool(
    name="canvas_list_courses",
    annotations={
        "title": "List Canvas Courses",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_list_courses(params: ListCoursesInput) -> str:
    """
    List the user's enrolled Canvas courses.

    Returns a summary of each course including name, course code, ID, and term.
    Use the course IDs returned here with other canvas_ tools.

    Args:
        params (ListCoursesInput):
            - include_concluded (bool): Whether to include past/concluded courses. Default: False.

    Returns:
        str: Markdown-formatted list of courses with IDs and details.

    Examples:
        - Use when: "What courses am I in?" -> canvas_list_courses()
        - Use when: "Show me all my classes" -> canvas_list_courses()
        - Use before: Any tool that needs a course_id
    """
    err = _check_config()
    if err:
        return err
    try:
        enrollment_state = "active" if not params.include_concluded else None
        query_params = {"per_page": 50}
        if enrollment_state:
            query_params["enrollment_state"] = enrollment_state

        courses = await _get("courses", params=query_params)

        if not courses:
            return "No active courses found. Try again with include_concluded=True to see past courses."

        lines = ["# Your Canvas Courses\n"]
        for c in courses:
            cid = c.get("id", "?")
            name = c.get("name", "Unnamed")
            code = c.get("course_code", "")
            term = c.get("enrollment_term_id", "")
            workflow = c.get("workflow_state", "")
            lines.append(f"## {name}")
            lines.append(f"- **Course ID**: `{cid}`")
            if code:
                lines.append(f"- **Code**: {code}")
            if workflow:
                lines.append(f"- **Status**: {workflow}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_get_upcoming_assignments",
    annotations={
        "title": "Get Upcoming Assignments (All Courses)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_get_upcoming_assignments(params: UpcomingAssignmentsInput) -> str:
    """
    Get all upcoming assignments across ALL active courses, sorted by due date.

    This is the most useful tool for a daily morning briefing — it surfaces
    everything due in the next N days across every class in one call.

    Args:
        params (UpcomingAssignmentsInput):
            - days_ahead (int): How many days ahead to look. Default: 14.
            - include_no_due_date (bool): Include assignments with no due date. Default: False.

    Returns:
        str: Markdown list of upcoming assignments sorted by due date, with urgency labels.

    Examples:
        - Use when: "What's due this week?" -> canvas_get_upcoming_assignments(days_ahead=7)
        - Use when: "Show me everything due in the next two weeks" -> canvas_get_upcoming_assignments(days_ahead=14)
        - Use when: Running the morning briefing -> canvas_get_upcoming_assignments(days_ahead=7)
    """
    err = _check_config()
    if err:
        return err
    try:
        courses = await _get("courses", params={"enrollment_state": "active", "per_page": 50})

        if not courses:
            return "No active courses found."

        all_assignments = []

        for course in courses:
            cid = course.get("id")
            cname = course.get("name", "Unknown Course")
            try:
                assignments = await _get(
                    f"courses/{cid}/assignments",
                    params={"per_page": 50, "order_by": "due_at"}
                )
                for a in assignments:
                    a["_course_name"] = cname
                all_assignments.extend(assignments)
            except Exception:
                continue  # Skip courses we can't access

        now = datetime.now(timezone.utc)
        upcoming = []
        for a in all_assignments:
            due = a.get("due_at")
            days = _days_until(due)
            if due is None:
                if params.include_no_due_date:
                    upcoming.append((None, a))
                continue
            if 0 <= days <= params.days_ahead:
                upcoming.append((days, a))

        # Sort by days until due
        upcoming.sort(key=lambda x: (x[0] is None, x[0] or 999))

        if not upcoming:
            return f"No assignments due in the next {params.days_ahead} days. "

        lines = [f"# Upcoming Assignments — Next {params.days_ahead} Days\n"]
        lines.append(f"Found **{len(upcoming)}** assignment(s).\n")

        for days, a in upcoming:
            name = a.get("name", "Unnamed")
            course = a.get("_course_name", "Unknown")
            due = a.get("due_at")
            pts = a.get("points_possible")
            submitted = a.get("has_submitted_submissions", False)
            url = a.get("html_url", "")

            urgency = _urgency_label(days)
            submitted_tag = " ✅ Submitted" if submitted else ""

            lines.append(f"### {name}{urgency}{submitted_tag}")
            lines.append(f"- **Course**: {course}")
            lines.append(f"- **Due**: {_fmt_date(due)}")
            if pts is not None:
                lines.append(f"- **Points**: {pts}")
            if url:
                lines.append(f"- **Link**: {url}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_list_assignments",
    annotations={
        "title": "List Assignments for a Course",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_list_assignments(params: ListAssignmentsInput) -> str:
    """
    List all assignments for a specific Canvas course.

    Use canvas_list_courses first to get the course_id.

    Args:
        params (ListAssignmentsInput):
            - course_id (str): The Canvas course ID (required).
            - upcoming_only (bool): Only show assignments with future due dates. Default: False.
            - include_submitted (bool): Include already-submitted assignments. Default: True.

    Returns:
        str: Markdown list of assignments with due dates, points, and submission status.

    Examples:
        - Use when: "Show me all assignments for CS101" -> canvas_list_assignments(course_id="12345")
        - Use when: "What's left to do in my algorithms class?" -> canvas_list_assignments(course_id="...", upcoming_only=True, include_submitted=False)
    """
    err = _check_config()
    if err:
        return err
    try:
        assignments = await _get(
            f"courses/{params.course_id}/assignments",
            params={"per_page": 50, "order_by": "due_at"}
        )

        if not assignments:
            return f"No assignments found for course {params.course_id}."

        filtered = []
        for a in assignments:
            days = _days_until(a.get("due_at"))
            if params.upcoming_only and (days is None or days < 0):
                continue
            if not params.include_submitted and a.get("has_submitted_submissions"):
                continue
            filtered.append(a)

        if not filtered:
            return "No assignments match the specified filters."

        lines = [f"# Assignments for Course {params.course_id}\n"]
        for a in filtered:
            name = a.get("name", "Unnamed")
            due = a.get("due_at")
            pts = a.get("points_possible")
            submitted = a.get("has_submitted_submissions", False)
            url = a.get("html_url", "")
            days = _days_until(due)
            urgency = _urgency_label(days)
            submitted_tag = " ✅" if submitted else ""

            lines.append(f"### {name}{urgency}{submitted_tag}")
            lines.append(f"- **Due**: {_fmt_date(due)}")
            if pts is not None:
                lines.append(f"- **Points**: {pts}")
            desc = a.get("description", "")
            if desc:
                # Strip HTML tags for a plain text preview
                import re
                clean = re.sub(r"<[^>]+>", "", desc)[:200].strip()
                if clean:
                    lines.append(f"- **Description**: {clean}{'...' if len(clean) == 200 else ''}")
            if url:
                lines.append(f"- **Link**: {url}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_get_missing_submissions",
    annotations={
        "title": "Get Missing/Overdue Submissions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_get_missing_submissions() -> str:
    """
    Get all missing or overdue assignment submissions across all courses.

    These are assignments that are past their due date and have not been submitted.
    Useful for catching anything that slipped through the cracks.

    Returns:
        str: Markdown list of missing submissions sorted by how overdue they are.

    Examples:
        - Use when: "What have I missed?" -> canvas_get_missing_submissions()
        - Use when: "Am I missing any assignments?" -> canvas_get_missing_submissions()
    """
    err = _check_config()
    if err:
        return err
    try:
        missing = await _get(
            "users/self/missing_submissions",
            params={"per_page": 50, "include[]": "course"}
        )

        if not missing:
            return "No missing submissions found. You're all caught up! ✅"

        lines = [f"# Missing Submissions ({len(missing)} total)\n"]

        for a in missing:
            name = a.get("name", "Unnamed")
            due = a.get("due_at")
            pts = a.get("points_possible")
            url = a.get("html_url", "")
            course_id = a.get("course_id", "")
            days = _days_until(due)
            days_str = f"{abs(days)} day(s) overdue" if days is not None and days < 0 else "past due"

            lines.append(f"### {name}")
            lines.append(f"- **Course ID**: {course_id}")
            lines.append(f"- **Was Due**: {_fmt_date(due)} ({days_str})")
            if pts is not None:
                lines.append(f"- **Points**: {pts}")
            if url:
                lines.append(f"- **Link**: {url}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_list_announcements",
    annotations={
        "title": "List Course Announcements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_list_announcements(params: AnnouncementsInput) -> str:
    """
    Get recent announcements from all active Canvas courses.

    Surfaces announcements from professors/instructors posted in the last N days.
    Useful for catching updates you may have missed.

    Args:
        params (AnnouncementsInput):
            - days_back (int): How many days back to look. Default: 7.

    Returns:
        str: Markdown list of announcements with course, title, date, and preview.

    Examples:
        - Use when: "Any announcements from my professors?" -> canvas_list_announcements()
        - Use when: "What did my instructors post this week?" -> canvas_list_announcements(days_back=7)
    """
    err = _check_config()
    if err:
        return err
    try:
        courses = await _get("courses", params={"enrollment_state": "active", "per_page": 50})

        if not courses:
            return "No active courses found."

        context_codes = [f"course_{c['id']}" for c in courses if c.get("id")]

        if not context_codes:
            return "Could not build context codes for courses."

        url = f"{CANVAS_BASE_URL}/api/v1/announcements"
        results = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(
                    url,
                    headers=_headers(),
                    params=[("context_codes[]", cc) for cc in context_codes] + [("per_page", "50")]
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)

                next_url = None
                link_header = response.headers.get("Link", "")
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
                        break
                url = next_url

        # Filter to days_back window
        now = datetime.now(timezone.utc)
        filtered = []
        for a in results:
            posted = a.get("posted_at") or a.get("created_at")
            if posted:
                try:
                    dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                    if (now - dt).days <= params.days_back:
                        filtered.append(a)
                except Exception:
                    filtered.append(a)

        if not filtered:
            return f"No announcements in the last {params.days_back} days."

        import re
        lines = [f"# Announcements — Last {params.days_back} Days\n"]
        lines.append(f"Found **{len(filtered)}** announcement(s).\n")

        for a in filtered:
            title = a.get("title", "No title")
            posted = a.get("posted_at") or a.get("created_at")
            author = a.get("author", {}).get("display_name", "Unknown")
            context = a.get("context_name", a.get("course_id", ""))
            body = a.get("message", "")
            clean_body = re.sub(r"<[^>]+>", "", body)[:300].strip()
            url_link = a.get("html_url", "")

            lines.append(f"### {title}")
            lines.append(f"- **Course**: {context}")
            lines.append(f"- **From**: {author}")
            lines.append(f"- **Posted**: {_fmt_date(posted)}")
            if clean_body:
                lines.append(f"- **Preview**: {clean_body}{'...' if len(clean_body) == 300 else ''}")
            if url_link:
                lines.append(f"- **Link**: {url_link}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_get_todo",
    annotations={
        "title": "Get Canvas To-Do Items",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_get_todo() -> str:
    """
    Get the current Canvas to-do list for the authenticated user.

    Canvas surfaces items that need action — typically unsubmitted assignments,
    ungraded quizzes, and other pending tasks.

    Returns:
        str: Markdown list of to-do items with due dates and course info.

    Examples:
        - Use when: "What's on my Canvas to-do list?" -> canvas_get_todo()
        - Use when: "What does Canvas think I need to do?" -> canvas_get_todo()
    """
    err = _check_config()
    if err:
        return err
    try:
        todo = await _get("users/self/todo", params={"per_page": 50})

        if not todo:
            return "Your Canvas to-do list is empty. ✅"

        lines = [f"# Canvas To-Do ({len(todo)} item(s))\n"]

        for item in todo:
            item_type = item.get("type", "")
            assignment = item.get("assignment", {})
            name = assignment.get("name", item.get("context_name", "Unknown"))
            course = item.get("context_name", "")
            due = assignment.get("due_at")
            url_link = assignment.get("html_url", "")
            days = _days_until(due)
            urgency = _urgency_label(days)

            lines.append(f"### {name}{urgency}")
            lines.append(f"- **Type**: {item_type}")
            if course:
                lines.append(f"- **Course**: {course}")
            lines.append(f"- **Due**: {_fmt_date(due)}")
            if url_link:
                lines.append(f"- **Link**: {url_link}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="canvas_get_grades",
    annotations={
        "title": "Get Current Grades",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def canvas_get_grades(params: CourseGradesInput) -> str:
    """
    Get current grades for all active courses (or a specific course).

    Returns current score, final score, and letter grade where available.

    Args:
        params (CourseGradesInput):
            - course_id (Optional[str]): Specific course ID, or omit for all courses.

    Returns:
        str: Markdown table of courses with current grades and scores.

    Examples:
        - Use when: "What are my current grades?" -> canvas_get_grades()
        - Use when: "What's my grade in CS301?" -> canvas_get_grades(course_id="12345")
    """
    err = _check_config()
    if err:
        return err
    try:
        if params.course_id:
            enrollments = await _get(
                f"courses/{params.course_id}/enrollments",
                params={"user_id": "self", "per_page": 50}
            )
            courses_to_check = [(params.course_id, params.course_id)]
        else:
            courses = await _get("courses", params={"enrollment_state": "active", "per_page": 50, "include[]": "total_scores"})
            if not courses:
                return "No active courses found."
            courses_to_check = [(c.get("id"), c.get("name", f"Course {c.get('id')}")) for c in courses]

        lines = ["# Current Grades\n"]
        found_any = False

        for cid, cname in courses_to_check:
            try:
                enrollments = await _get(
                    f"courses/{cid}/enrollments",
                    params={"user_id": "self", "type[]": "StudentEnrollment", "per_page": 10}
                )
                for e in enrollments:
                    grades = e.get("grades", {})
                    current_score = grades.get("current_score")
                    final_score = grades.get("final_score")
                    current_grade = grades.get("current_grade")
                    final_grade = grades.get("final_grade")

                    score_str = f"{current_score}%" if current_score is not None else "N/A"
                    grade_str = current_grade or final_grade or "N/A"

                    lines.append(f"### {cname}")
                    lines.append(f"- **Current Score**: {score_str}")
                    lines.append(f"- **Letter Grade**: {grade_str}")
                    if final_score and final_score != current_score:
                        lines.append(f"- **Final Score**: {final_score}%")
                    lines.append("")
                    found_any = True
            except Exception:
                continue

        if not found_any:
            return "No grade data found. Grades may not be released yet, or you're not enrolled as a student."

        return "\n".join(lines)
    except Exception as e:
        return _handle_error(e)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

