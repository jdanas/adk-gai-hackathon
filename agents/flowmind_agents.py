from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from config import get_settings
from tools.mcp_tools import book_calendar_tool, create_task_tool, retrieve_notes_tool

settings = get_settings()


@dataclass
class AgentDefinition:
    name: str
    model: str
    description: str
    instruction: str
    tools: list[Callable[..., Any]] | None = None
    sub_agents: list["AgentDefinition"] | None = None


def _build_agent(
    *,
    name: str,
    model: str,
    description: str,
    instruction: str,
    tools: list[Callable[..., Any]] | None = None,
    sub_agents: list[AgentDefinition] | None = None,
) -> Any:
    if settings.flowmind_enable_adk:
        from google.adk.agents import Agent

        return Agent(
            name=name,
            model=model,
            description=description,
            instruction=instruction,
            tools=tools,
            sub_agents=sub_agents,
        )
    return AgentDefinition(
        name=name,
        model=model,
        description=description,
        instruction=instruction,
        tools=tools,
        sub_agents=sub_agents,
    )


def _make_embedding(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = list(digest) * ((dimensions // len(digest)) + 1)
    normalized = [(byte / 255.0) for byte in seed[:dimensions]]
    return normalized


def _extract_title(prompt: str, fallback: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        return fallback
    return cleaned[:80]


def _extract_time_window(prompt: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    match = re.search(r"(\d+)\s*(minute|minutes|hour|hours)", prompt, flags=re.IGNORECASE)
    if not match:
        start = now + timedelta(hours=1)
        end = start + timedelta(hours=1)
        return start, end

    quantity = int(match.group(1))
    unit = match.group(2).lower()
    duration = timedelta(minutes=quantity) if "minute" in unit else timedelta(hours=quantity)
    start = now + timedelta(hours=1)
    end = start + duration
    return start, end


@dataclass
class AgentAction:
    type: str
    action: str
    details: str

    def as_dict(self) -> dict[str, str]:
        return {
            "type": self.type,
            "action": self.action,
            "details": self.details,
        }


class TaskAgentService:
    def __init__(self) -> None:
        self.agent = _build_agent(
            name="task_agent",
            model=settings.vertex_ai_model,
            description="Creates and manages task records.",
            instruction=(
                "You are the FlowMind Task Agent. Convert user intent into task creation "
                "operations using the create_task tool."
            ),
            tools=[create_task_tool],
        )

    async def handle(self, prompt: str) -> AgentAction:
        title = _extract_title(prompt, "Untitled task")
        result = await create_task_tool(title=title)
        return AgentAction(
            type="task_agent",
            action=result["action"],
            details=result["details"],
        )


class CalendarAgentService:
    def __init__(self) -> None:
        self.agent = _build_agent(
            name="calendar_agent",
            model=settings.vertex_ai_model,
            description="Books calendar events after availability checks.",
            instruction=(
                "You are the FlowMind Calendar Agent. Interpret scheduling intent and use "
                "the book_calendar tool to create events only when the time slot is free."
            ),
            tools=[book_calendar_tool],
        )

    async def handle(self, prompt: str) -> AgentAction:
        start_time, end_time = _extract_time_window(prompt)
        title = _extract_title(prompt, "FlowMind event")
        result = await book_calendar_tool(title=title, start_time=start_time, end_time=end_time)
        return AgentAction(
            type="calendar_agent",
            action=result["action"],
            details=result["details"],
        )


class NotesAgentService:
    def __init__(self) -> None:
        self.agent = _build_agent(
            name="notes_agent",
            model=settings.vertex_ai_model,
            description="Retrieves semantically similar notes.",
            instruction=(
                "You are the FlowMind Notes Agent. Transform the user query into a semantic "
                "search request and use retrieve_notes to fetch matching notes."
            ),
            tools=[retrieve_notes_tool],
        )

    async def handle(self, prompt: str) -> AgentAction:
        embedding = _make_embedding(prompt, settings.notes_embedding_dim)
        result = await retrieve_notes_tool(query_embedding=embedding)
        return AgentAction(
            type="notes_agent",
            action=result["action"],
            details=result["details"],
        )


class OrchestratorAgentService:
    def __init__(self) -> None:
        self.task_agent = TaskAgentService()
        self.calendar_agent = CalendarAgentService()
        self.notes_agent = NotesAgentService()
        self.agent = _build_agent(
            name="orchestrator_agent",
            model=settings.vertex_ai_model,
            description="Semantic router and aggregator for FlowMind.",
            instruction=(
                "You are the FlowMind Orchestrator Agent. Act only as a semantic router. "
                "Read the user's raw request, identify whether task management, calendar "
                "booking, note retrieval, or any combination is required, dispatch the "
                "request to the appropriate sub-agents concurrently, and aggregate a "
                "structured summary of actions taken. Never fabricate tool results."
            ),
            sub_agents=[
                self.task_agent.agent,
                self.calendar_agent.agent,
                self.notes_agent.agent,
            ],
        )

    async def orchestrate(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower()
        coroutines = []

        if any(keyword in lowered for keyword in ["task", "todo", "to-do", "follow up", "remind"]):
            coroutines.append(self.task_agent.handle(prompt))
        if any(keyword in lowered for keyword in ["calendar", "schedule", "meeting", "book", "event"]):
            coroutines.append(self.calendar_agent.handle(prompt))
        if any(keyword in lowered for keyword in ["note", "notes", "remember", "knowledge", "search"]):
            coroutines.append(self.notes_agent.handle(prompt))

        if not coroutines:
            coroutines = [
                self.task_agent.handle(prompt),
                self.calendar_agent.handle(prompt),
                self.notes_agent.handle(prompt),
            ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        actions: list[dict[str, str]] = []
        for result in results:
            if isinstance(result, Exception):
                actions.append(
                    AgentAction(
                        type="orchestrator_agent",
                        action="agent_error",
                        details=str(result),
                    ).as_dict()
                )
                continue
            actions.append(result.as_dict())

        return {
            "status": "success",
            "actions": actions,
            "router_trace": json.dumps(
                {
                    "task_agent": any(action["type"] == "task_agent" for action in actions),
                    "calendar_agent": any(action["type"] == "calendar_agent" for action in actions),
                    "notes_agent": any(action["type"] == "notes_agent" for action in actions),
                }
            ),
        }
