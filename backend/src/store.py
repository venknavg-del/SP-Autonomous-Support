"""
Incident Store — Database-backed persistence (Oracle or SQLite).
Stores incident state and agent reasoning events.
WebSocket pub/sub remains in-memory for real-time streaming.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.db import execute, fetch_one, fetch_all, DB_MODE

logger = logging.getLogger("store")


class IncidentStore:
    """Database-backed incident store with in-memory WebSocket pub/sub."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    # ── Create ────────────────────────────────────────────────────

    def create(self, incident_id: str, scenario_id: str, source: str, raw_description: str):
        """Insert a new incident into the database."""
        now = datetime.now().isoformat()
        execute(
            """INSERT INTO SP_INCIDENTS 
               (incident_id, scenario_id, source, raw_description, status, created_at, errors)
               VALUES (:incident_id, :scenario_id, :source, :raw_description, :status, :created_at, :errors)""",
            {
                "incident_id": incident_id,
                "scenario_id": scenario_id,
                "source": source,
                "raw_description": raw_description,
                "status": "Processing",
                "created_at": now,
                "errors": "[]"
            }
        )
        logger.info(f"Incident {incident_id} created in DB")

    # ── Read ──────────────────────────────────────────────────────

    def get(self, incident_id: str) -> Optional[Dict]:
        """Fetch full incident detail with agent events."""
        row = fetch_one(
            "SELECT * FROM SP_INCIDENTS WHERE incident_id = :incident_id",
            {"incident_id": incident_id}
        )
        if not row:
            return None
        return self._row_to_dict(row)

    def get_with_events(self, incident_id: str) -> Optional[Dict]:
        """Fetch incident + full agent reasoning chain."""
        incident = self.get(incident_id)
        if not incident:
            return None
        
        events = fetch_all(
            """SELECT agent, action, source, created_at 
               FROM SP_AGENT_EVENTS 
               WHERE incident_id = :incident_id 
               ORDER BY event_id ASC""",
            {"incident_id": incident_id}
        )
        incident["agent_events"] = [
            {
                "agent": e["agent"],
                "action": e["action"],
                "source": e["source"],
                "timestamp": e["created_at"]
            }
            for e in events
        ]
        return incident

    def list_all(self) -> List[Dict]:
        """List all incidents (newest first)."""
        rows = fetch_all(
            """SELECT incident_id, source, raw_description, status, severity, 
                      issue_type, confidence_score, created_at
               FROM SP_INCIDENTS ORDER BY created_at DESC"""
        )
        return [
            {
                "incident_id": r["incident_id"],
                "source": r["source"],
                "desc": (r.get("raw_description") or "")[:120],
                "status": r["status"],
                "severity": r["severity"],
                "issue_type": r["issue_type"],
                "confidence_score": float(r["confidence_score"] or 0),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ── Update ────────────────────────────────────────────────────

        jira_context_json = json.dumps(state.get("jira_context")) if state.get("jira_context") else None
        errors_json = json.dumps(state.get("errors", []))
        execute(
            """UPDATE SP_INCIDENTS SET
                severity = :severity,
                issue_type = :issue_type,
                root_cause_analysis = :rca,
                suggested_resolution = :resolution,
                workaround = :workaround,
                recommended_runbook = :runbook,
                confidence_score = :confidence,
                requires_human_approval = :approval,
                jira_ticket_key = :jira_key,
                jira_context = :jira_context,
                errors = :errors
               WHERE incident_id = :incident_id""",
            {
                "severity": state.get("severity"),
                "issue_type": state.get("issue_type"),
                "rca": state.get("root_cause_analysis", ""),
                "resolution": state.get("suggested_resolution", ""),
                "workaround": state.get("workaround"),
                "runbook": state.get("recommended_runbook"),
                "confidence": state.get("confidence_score", 0),
                "approval": 1 if state.get("requires_human_approval") else 0,
                "jira_key": state.get("jira_ticket_key"),
                "jira_context": jira_context_json,
                "errors": errors_json,
                "incident_id": incident_id,
            }
        )

    def set_status(self, incident_id: str, status: str):
        """Update incident status."""
        params = {"status": status, "incident_id": incident_id}
        if status == "Resolved":
            params["resolved_at"] = datetime.now().isoformat()
            execute(
                "UPDATE SP_INCIDENTS SET status = :status, resolved_at = :resolved_at WHERE incident_id = :incident_id",
                params
            )
        else:
            execute(
                "UPDATE SP_INCIDENTS SET status = :status WHERE incident_id = :incident_id",
                params
            )

    def approve(self, incident_id: str) -> bool:
        """Approve a pending human approval."""
        row = fetch_one(
            "SELECT requires_human_approval, human_approved FROM SP_INCIDENTS WHERE incident_id = :incident_id",
            {"incident_id": incident_id}
        )
        if not row:
            return False
        if not row.get("requires_human_approval") or row.get("human_approved"):
            return False
        
        execute(
            """UPDATE SP_INCIDENTS SET 
                human_approved = 1, 
                status = :status 
               WHERE incident_id = :incident_id""",
            {"status": "Approved — Executing Fix", "incident_id": incident_id}
        )
        return True

    # ── Agent Events (Reasoning Chain) ────────────────────────────

    async def add_event(self, incident_id: str, agent: str, action: str, source: str = "System"):
        """Add an agent reasoning step to the DB and broadcast via WebSocket."""
        now = datetime.now().isoformat()
        execute(
            """INSERT INTO SP_AGENT_EVENTS (incident_id, agent, action, source, created_at)
               VALUES (:incident_id, :agent, :action, :source, :created_at)""",
            {
                "incident_id": incident_id,
                "agent": agent,
                "action": action,
                "source": source,
                "created_at": now,
            }
        )
        # Also broadcast to WebSocket subscribers for real-time updates
        await self._broadcast(incident_id, {
            "type": "agent_event",
            "data": {"agent": agent, "action": action, "source": source, "timestamp": now}
        })

    # ── WebSocket Pub/Sub (in-memory) ─────────────────────────────

    async def broadcast_status(self, incident_id: str, status: str):
        self.set_status(incident_id, status)
        await self._broadcast(incident_id, {"type": "status_update", "data": {"status": status}})

    def subscribe(self, incident_id: str) -> asyncio.Queue:
        if incident_id not in self._subscribers:
            self._subscribers[incident_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[incident_id].append(queue)
        return queue

    def unsubscribe(self, incident_id: str, queue: asyncio.Queue):
        if incident_id in self._subscribers:
            self._subscribers[incident_id] = [q for q in self._subscribers[incident_id] if q is not queue]

    async def _broadcast(self, incident_id: str, message: dict):
        for queue in self._subscribers.get(incident_id, []):
            await queue.put(message)

    # ── Helpers ───────────────────────────────────────────────────

    def _row_to_dict(self, row: dict) -> dict:
        """Convert a DB row to a frontend-compatible dict."""
        errors = []
        if row.get("errors"):
            try:
                errors = json.loads(row["errors"])
            except (json.JSONDecodeError, TypeError):
                errors = []

        jira_context = None
        if row.get("jira_context"):
            try:
                jira_context = json.loads(row["jira_context"])
            except (json.JSONDecodeError, TypeError):
                pass
                
        return {
            "incident_id": row["incident_id"],
            "scenario_id": row.get("scenario_id", ""),
            "source": row.get("source", ""),
            "raw_description": row.get("raw_description", ""),
            "status": row.get("status", "Processing"),
            "severity": row.get("severity"),
            "issue_type": row.get("issue_type"),
            "root_cause_analysis": row.get("root_cause_analysis", ""),
            "suggested_resolution": row.get("suggested_resolution", ""),
            "workaround": row.get("workaround"),
            "recommended_runbook": row.get("recommended_runbook"),
            "confidence_score": float(row.get("confidence_score") or 0),
            "requires_human_approval": bool(row.get("requires_human_approval")),
            "human_approved": bool(row.get("human_approved")) if row.get("human_approved") is not None else None,
            "jira_ticket_key": row.get("jira_ticket_key"),
            "jira_context": jira_context,
            "errors": errors,
            "created_at": row.get("created_at", ""),
            "resolved_at": row.get("resolved_at"),
            "agent_events": [],  # Populated by get_with_events()
        }


# Singleton
incident_store = IncidentStore()
