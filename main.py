from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.routing import Mount

from agents.flowmind_agents import OrchestratorAgentService
from config import get_settings
from db.connection import db_manager
from tools.mcp_tools import mcp_server

settings = get_settings()
orchestrator = OrchestratorAgentService()


class HealthResponse(BaseModel):
    status: str
    service: str


class OrchestrateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Unstructured user request.")


class ActionResponse(BaseModel):
    type: str
    action: str
    details: str


class OrchestrateResponse(BaseModel):
    status: str
    actions: list[ActionResponse]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db_manager.connect()
    try:
        async with mcp_server.session_manager.run():
            yield
    finally:
        await db_manager.disconnect()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.router.routes.append(Mount("/mcp", app=mcp_server.streamable_http_app()))


@app.get("/healthz", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@app.post("/api/v1/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    try:
        result = await orchestrator.orchestrate(request.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FlowMind orchestration failed: {exc}") from exc

    return OrchestrateResponse(
        status=result["status"],
        actions=[ActionResponse(**action) for action in result["actions"]],
    )
