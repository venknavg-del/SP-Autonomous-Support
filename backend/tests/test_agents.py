"""
Unit Tests — Tests each agent, PII filter, RBAC, and store in isolation.
Run: python -m pytest tests/test_agents.py -v
"""

import asyncio
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.schemas.state import IncidentState
from src.pii_filter import filter_pii
from src.rbac import can_auto_remediate, get_approval_level
from src.store import IncidentStore


def _make_state(**overrides) -> IncidentState:
    """Create a test IncidentState with sensible defaults."""
    base = {
        "incident_id": "INC-TEST001",
        "scenario_id": "scenario1_payment_bug",
        "source": "test",
        "raw_description": "Test incident: NullPointerException in PaymentService",
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
    }
    base.update(overrides)
    return IncidentState(base)


# ── PII Filter Tests ──────────────────────────────────────────────

class TestPIIFilter:
    def test_filters_email(self):
        result = filter_pii("Contact admin@company.com for help")
        assert "[EMAIL_REDACTED]" in result
        assert "admin@company.com" not in result

    def test_filters_ip(self):
        result = filter_pii("Server 192.168.1.100 is down")
        assert "[IP_REDACTED]" in result
        assert "192.168.1.100" not in result

    def test_filters_github_token(self):
        result = filter_pii("Token: ghp_abcdef1234567890abcdef1234567890abcd")
        assert "[GITHUB_TOKEN_REDACTED]" in result

    def test_preserves_normal_text(self):
        text = "NullPointerException in PaymentService at line 145"
        assert filter_pii(text) == text

    def test_handles_none(self):
        assert filter_pii("") == ""


# ── RBAC Tests ────────────────────────────────────────────────────

class TestRBAC:
    def test_infra_auto_remediate(self):
        assert can_auto_remediate("INFRA") is True

    def test_code_requires_approval(self):
        assert can_auto_remediate("CODE") is False
        assert get_approval_level("CODE") == "L3"

    def test_data_requires_l2(self):
        assert can_auto_remediate("DATA") is False
        assert get_approval_level("DATA") == "L2"

    def test_unknown_escalates(self):
        assert can_auto_remediate("UNKNOWN") is False
        assert get_approval_level("UNKNOWN") == "L1"

    def test_infra_no_approval(self):
        assert get_approval_level("INFRA") is None


# ── Store Tests ───────────────────────────────────────────────────

class TestStore:
    def test_create_and_get(self):
        store = IncidentStore()
        store.create("INC-001", "scenario1", "test", "Test description")
        inc = store.get("INC-001")
        assert inc is not None
        assert inc.incident_id == "INC-001"
        assert inc.status == "Processing"

    def test_list_all(self):
        store = IncidentStore()
        store.create("INC-001", "s1", "test", "Desc 1")
        store.create("INC-002", "s2", "test", "Desc 2")
        items = store.list_all()
        assert len(items) == 2

    def test_approve(self):
        store = IncidentStore()
        store.create("INC-001", "s1", "test", "Desc")
        inc = store.get("INC-001")
        inc.requires_human_approval = True
        assert store.approve("INC-001") is True
        assert inc.human_approved is True

    def test_approve_not_needed(self):
        store = IncidentStore()
        store.create("INC-001", "s1", "test", "Desc")
        assert store.approve("INC-001") is False

    def test_set_status(self):
        store = IncidentStore()
        store.create("INC-001", "s1", "test", "Desc")
        store.set_status("INC-001", "Resolved")
        assert store.get("INC-001").status == "Resolved"
        assert store.get("INC-001").resolved_at is not None


# ── Agent Tests ───────────────────────────────────────────────────

class TestAgents:
    def test_triage_node(self):
        """Test that triage_node classifies severity."""
        state = _make_state(raw_description="Site is down, payment gateway timeout")
        # The LLM mock should classify "down" as P1
        from src.agents.triage import triage_node
        result = asyncio.run(triage_node(state))
        assert result["severity"] in ["P1", "P2", "P3"]
        assert result["current_agent"] == "triage"

    def test_resolution_node_code(self):
        state = _make_state(issue_type="CODE", raw_description="NPE in PaymentService")
        from src.agents.resolution import resolution_node
        result = asyncio.run(resolution_node(state))
        assert result["requires_human_approval"] is True
        assert result["confidence_score"] > 0

    def test_resolution_node_infra(self):
        state = _make_state(issue_type="INFRA", raw_description="DB pool exhausted")
        from src.agents.resolution import resolution_node
        result = asyncio.run(resolution_node(state))
        assert result["requires_human_approval"] is False

    def test_supervisor_routing(self):
        from src.agents.supervisor import supervisor_node
        assert supervisor_node(_make_state(current_agent="start")) == "triage"
        assert supervisor_node(_make_state(current_agent="triage")) == "telemetry"
        assert supervisor_node(_make_state(current_agent="codebase")) == "resolution"
        assert supervisor_node(_make_state(current_agent="resolution")) == "__end__"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
