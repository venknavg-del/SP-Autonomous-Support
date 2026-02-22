"""
SP Autonomous Production Support — FastAPI Application
=====================================================
Endpoints:
  POST /api/v1/incidents/submit  — Submit a new incident
  GET  /api/v1/incidents         — List all incidents
  GET  /api/v1/incidents/{id}    — Get incident detail
  POST /api/v1/incidents/{id}/approve — Approve a pending fix
  GET  /api/v1/metrics           — System metrics
  WS   /ws/incidents/{id}        — Live agent progress stream
  GET  /health                   — Health check
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import asyncio
from pathlib import Path

from src.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger("main")

from src.orchestrator.graph import incident_orchestrator
from src.schemas.state import IncidentState
from src.store import incident_store
from src.pii_filter import filter_pii
from src.db import run_migration, DB_MODE
from src.services.email_poller import start_poller_background_task

# ── App Setup ─────────────────────────────────────────────────────────

app = FastAPI(
    title="SP Autonomous Production Support API",
    description="Agentic Orchestrator driven by LangGraph and MCP for automated production incident resolution.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB Init ────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_db():
    logger.info(f"Database mode: {DB_MODE}")
    run_migration()
    # Start the email watcher in the background
    start_poller_background_task()

# ── Metrics ───────────────────────────────────────────────────────────

_metrics = {
    "total_incidents": 0,
    "resolved_count": 0,
    "auto_remediated_count": 0,
    "avg_resolution_time_ms": 0,
    "resolution_times": [],
    "agent_durations": {},
}

# ── Request Model ─────────────────────────────────────────────────────

class IncidentRequest(BaseModel):
    source: str
    raw_description: Optional[str] = ""
    scenario_id: Optional[str] = "scenario1_payment_bug"

class EnvUpdateRequest(BaseModel):
    content: str

# ── Orchestrator Runner ──────────────────────────────────────────────

async def run_orchestrator(incident_id: str, request: IncidentRequest):
    """Background task: runs the LangGraph workflow and streams events."""
    logger.info(f"Starting workflow for {incident_id} [Scenario: {request.scenario_id}]")
    start_time = time.time()

    initial_state = IncidentState({
        "incident_id": incident_id,
        "scenario_id": request.scenario_id,
        "source": request.source,
        "raw_description": request.raw_description or "",
        "severity": None,
        "similar_historical_tickets": [],
        "relevant_runbooks": [],
        "splunk_logs": [],
        "identified_anomalies": [],
        "suspected_components": [],
        "code_snippets": [],
        "root_cause_analysis": "",
        "issue_type": None,
        "suggested_resolution": "",
        "confidence_score": 0.0,
        "requires_human_approval": False,
        "human_approved": None,
        "jira_ticket_key": None,
        "current_agent": "start",
        "errors": []
    })

    try:
        # Run with event streaming
        final_state = None
        agent_start = time.time()

        async for event in incident_orchestrator.astream(initial_state):
            for node_name, node_output in event.items():
                agent_dur = time.time() - agent_start
                _metrics["agent_durations"][node_name] = _metrics["agent_durations"].get(node_name, [])
                _metrics["agent_durations"][node_name].append(round(agent_dur * 1000))

                # Broadcast agent completion event via WebSocket
                action = _get_agent_summary(node_name, node_output)
                source = _get_agent_source(node_name)
                await incident_store.add_event(incident_id, node_name.title() + " Agent", action, source)
                logger.info(f"[{incident_id}] {node_name} completed in {agent_dur:.2f}s")

                final_state = node_output
                agent_start = time.time()

        if final_state:
            incident_store.update_from_state(incident_id, final_state)

            if final_state.get("requires_human_approval"):
                await incident_store.broadcast_status(incident_id, "Pending Human Approval")
            else:
                await incident_store.broadcast_status(incident_id, "Resolved")
                _metrics["auto_remediated_count"] += 1

            _metrics["resolved_count"] += 1

        duration_ms = round((time.time() - start_time) * 1000)
        _metrics["resolution_times"].append(duration_ms)
        _metrics["avg_resolution_time_ms"] = round(sum(_metrics["resolution_times"]) / len(_metrics["resolution_times"]))

        logger.info(f"Workflow complete for {incident_id} in {duration_ms}ms")

    except Exception as e:
        logger.error(f"Workflow failed for {incident_id}: {e}")
        await incident_store.add_event(incident_id, "System", f"Workflow Error: {str(e)}", "Error")
        await incident_store.broadcast_status(incident_id, "Failed")


def _get_agent_summary(node_name: str, output: dict) -> str:
    """Generate a human-readable summary from agent output."""
    if node_name == "triage":
        return f"Classified as {output.get('severity', 'N/A')}. Found {len(output.get('similar_historical_tickets', []))} similar tickets."
    elif node_name == "telemetry":
        anomalies = output.get("identified_anomalies", [])
        return f"Found {len(anomalies)} anomalies. Suspected components: {', '.join(output.get('suspected_components', []))}."
    elif node_name == "codebase":
        return f"Issue type: {output.get('issue_type', 'N/A')}. RCA: {output.get('root_cause_analysis', 'N/A')[:100]}"
    elif node_name == "resolution":
        return f"{output.get('suggested_resolution', 'N/A')[:120]} (Confidence: {output.get('confidence_score', 0):.0%})"
    return str(output)[:100]


def _get_agent_source(node_name: str) -> str:
    mode = os.getenv("INGESTION_MODE", "local")
    sources = {
        "triage": "Email MCP" if mode == "mcp" else "Local File",
        "telemetry": "Splunk MCP" if mode == "mcp" else "Local Logs",
        "codebase": "GitHub MCP" if mode == "mcp" else "Local Code",
        "resolution": "Jira + Outlook MCP" if mode == "mcp" else "Local Engine",
    }
    return sources.get(node_name, "System")


# ── API Endpoints ──────────────────────────────────────────────────────

@app.post("/api/v1/incidents/submit")
async def receive_incident(request: IncidentRequest, background_tasks: BackgroundTasks):
    """Submit a new incident to the agentic orchestrator."""
    ingestion_mode = os.getenv("INGESTION_MODE", "local").lower()
    if not request.raw_description and ingestion_mode != "local":
        raise HTTPException(status_code=400, detail="raw_description is required when INGESTION_MODE is not 'local'")

    incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"

    # Persist
    incident_store.create(incident_id, request.scenario_id, request.source, filter_pii(request.raw_description or ""))
    _metrics["total_incidents"] += 1

    background_tasks.add_task(run_orchestrator, incident_id, request)

    return {
        "status": "Accepted",
        "incident_id": incident_id,
        "message": "Incident received. Agentic Orchestrator has begun analysis."
    }


@app.get("/api/v1/incidents")
async def list_incidents():
    """List all incidents with summary info."""
    return {"incidents": incident_store.list_all()}


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get full detail for a specific incident including agent reasoning chain."""
    inc = incident_store.get_with_events(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return inc


@app.post("/api/v1/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str):
    """Approve a pending human approval for an incident resolution."""
    success = incident_store.approve(incident_id)
    if not success:
        inc = incident_store.get(incident_id)
        if not inc:
            raise HTTPException(status_code=404, detail="Incident not found")
        raise HTTPException(status_code=400, detail="Incident does not require approval or already approved")
    await incident_store.broadcast_status(incident_id, "Approved — Executing Fix")
    return {"status": "Approved", "incident_id": incident_id}


@app.get("/api/v1/metrics")
async def get_metrics():
    """System metrics: counts, timing, and agent performance."""
    agent_avg = {}
    for agent, times in _metrics["agent_durations"].items():
        agent_avg[agent] = {
            "avg_ms": round(sum(times) / len(times)) if times else 0,
            "max_ms": max(times) if times else 0,
            "count": len(times)
        }
    return {
        "total_incidents": _metrics["total_incidents"],
        "resolved_count": _metrics["resolved_count"],
        "auto_remediated_count": _metrics["auto_remediated_count"],
        "avg_resolution_time_ms": _metrics["avg_resolution_time_ms"],
        "agent_performance": agent_avg,
    }


# ── Configuration (Env) ────────────────────────────────────────────────

@app.get("/api/v1/config/env")
async def get_env_file():
    """Read the raw backend .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        return {"content": ""}
    with open(env_path, "r") as f:
        return {"content": f.read()}

@app.post("/api/v1/config/env")
async def update_env_file(request: EnvUpdateRequest):
    """Write the raw backend .env file."""
    env_path = Path(".env")
    with open(env_path, "w") as f:
        f.write(request.content)
    return {"message": ".env file updated successfully."}

@app.get("/api/v1/config/json")
async def get_env_json():
    """Read the .env file and return it as a JSON key-value map."""
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    
    config = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    return config

@app.post("/api/v1/config/json")
async def update_env_json(config: dict):
    """Update specific keys in the .env file while preserving comments."""
    env_path = Path(".env")
    if not env_path.exists():
        with open(env_path, "w") as f:
            for k, v in config.items():
                f.write(f"{k}={v}\n")
        return {"message": "Config created."}
        
    lines = []
    with open(env_path, "r") as f:
        lines = f.readlines()
        
    updated_keys = set()
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
            
        if "=" in stripped:
            key, val = stripped.split("=", 1)
            key = key.strip()
            if key in config:
                new_lines.append(f"{key}={config[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    # Add any new keys that weren't in the file
    for key, val in config.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")
            
    with open(env_path, "w") as f:
        f.writelines(new_lines)
        
    return {"message": "Config updated via JSON."}



# ── WebSocket ──────────────────────────────────────────────────────────

@app.websocket("/ws/incidents/{incident_id}")
async def websocket_endpoint(websocket: WebSocket, incident_id: str):
    """Stream live agent events for a specific incident."""
    await websocket.accept()
    queue = incident_store.subscribe(incident_id)
    logger.info(f"WebSocket connected for {incident_id}")

    try:
        # Send existing events from DB first
        inc = incident_store.get_with_events(incident_id)
        if inc:
            for event in inc.get("agent_events", []):
                await websocket.send_json({
                    "type": "agent_event",
                    "data": {"agent": event["agent"], "action": event["action"], "source": event["source"], "timestamp": event["timestamp"]}
                })
            await websocket.send_json({"type": "status_update", "data": {"status": inc.get("status", "Processing")}})

        # Stream new events
        while True:
            message = await asyncio.wait_for(queue.get(), timeout=300)
            await websocket.send_json(message)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        logger.info(f"WebSocket disconnected for {incident_id}")
    finally:
        incident_store.unsubscribe(incident_id, queue)


@app.get("/health")
def health_check():
    return {"status": "Healthy", "service": "SP-Autonomous-Support-AI-Engine", "version": "2.0.0"}
