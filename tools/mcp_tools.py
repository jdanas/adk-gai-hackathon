from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from config import get_settings
from db.connection import db_manager

settings = get_settings()
mcp_server = FastMCP(
    settings.mcp_server_name,
    stateless_http=True,
    json_response=True,
)


async def create_task_tool(title: str, status: str = "pending") -> dict[str, Any]:
    query = """
        INSERT INTO tasks (title, status)
        VALUES ($1, $2)
        RETURNING id, title, status, created_at;
    """
    async with db_manager.acquire() as connection:
        row = await connection.fetchrow(query, title, status)
    return {
        "type": "task",
        "action": "task_created",
        "details": f"Task '{row['title']}' created with status '{row['status']}'.",
        "record": dict(row),
    }


async def book_calendar_tool(
    title: str,
    start_time: datetime,
    end_time: datetime,
) -> dict[str, Any]:
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    conflict_query = """
        SELECT id, title, start_time, end_time
        FROM calendar_events
        WHERE start_time < $2 AND end_time > $1
        LIMIT 1;
    """
    insert_query = """
        INSERT INTO calendar_events (title, start_time, end_time)
        VALUES ($1, $2, $3)
        RETURNING id, title, start_time, end_time;
    """

    async with db_manager.acquire() as connection:
        conflict = await connection.fetchrow(conflict_query, start_time, end_time)
        if conflict:
            return {
                "type": "calendar",
                "action": "calendar_conflict",
                "details": (
                    f"Could not book '{title}'. Conflicts with '{conflict['title']}' "
                    f"from {conflict['start_time']} to {conflict['end_time']}."
                ),
                "record": dict(conflict),
            }
        row = await connection.fetchrow(insert_query, title, start_time, end_time)

    return {
        "type": "calendar",
        "action": "calendar_booked",
        "details": f"Booked '{row['title']}' from {row['start_time']} to {row['end_time']}.",
        "record": dict(row),
    }


async def retrieve_notes_tool(
    query_embedding: list[float],
    limit: int | None = None,
) -> dict[str, Any]:
    result_limit = limit or settings.flowmind_notes_default_limit
    query = """
        SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity
        FROM notes
        ORDER BY embedding <=> $1::vector
        LIMIT $2;
    """
    async with db_manager.acquire() as connection:
        rows = await connection.fetch(query, query_embedding, result_limit)

    notes = [
        {
            "id": str(row["id"]),
            "content": row["content"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]
    return {
        "type": "notes",
        "action": "notes_retrieved",
        "details": f"Retrieved {len(notes)} similar notes.",
        "record": {"matches": notes},
    }


@mcp_server.tool(name="create_task")
async def create_task_tool_mcp(title: str, status: str = "pending") -> dict[str, Any]:
    return await create_task_tool(title=title, status=status)


@mcp_server.tool(name="book_calendar")
async def book_calendar_tool_mcp(
    title: str,
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    return await book_calendar_tool(
        title=title,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
    )


@mcp_server.tool(name="retrieve_notes")
async def retrieve_notes_tool_mcp(
    query_embedding: list[float],
    limit: int | None = None,
) -> dict[str, Any]:
    return await retrieve_notes_tool(query_embedding=query_embedding, limit=limit)
