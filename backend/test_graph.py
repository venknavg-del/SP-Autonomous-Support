import os
import sys

# Load .env FIRST
from dotenv import load_dotenv
load_dotenv()

import asyncio
from src.orchestrator.graph import incident_orchestrator
from src.schemas.state import IncidentState
import uuid

async def test_run():
    print("Initializing test incident state...")
    incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"
    initial_state = IncidentState({
        "incident_id": incident_id,
        "scenario_id": "scenario1_payment_bug",
        "source": "email",
        "raw_description": "test direct script",
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
        "current_agent": "start",
        "errors": []
    })
    
    print("Running orchestrator...")
    try:
        final_state = await incident_orchestrator.ainvoke(initial_state)
        print(f"Workflow Complete. Resolution: {final_state.get('suggested_resolution')}")
        print("Final State Snippet:")
        print(final_state.get('issue_type'))
        print(final_state.get('root_cause_analysis'))
        print(final_state.get('severity'))
    except Exception as e:
        print(f"Workflow failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_run())
