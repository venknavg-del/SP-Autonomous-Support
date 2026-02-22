"""
RBAC Configuration — Role-Based Access Control for incident resolution.
Defines which issue types can be auto-remediated and which need human approval at what level.
"""

from typing import Dict, Any

# RBAC Rules: issue_type → approval requirements
RBAC_RULES: Dict[str, Dict[str, Any]] = {
    "INFRA": {
        "auto_remediate": True,
        "approval_level": None,  # No approval needed
        "description": "Infrastructure issues can be auto-remediated using known runbooks",
    },
    "CODE": {
        "auto_remediate": False,
        "approval_level": "L3",  # Requires L3 Engineering review
        "description": "Code changes always require L3 Engineering approval before merge",
    },
    "DATA": {
        "auto_remediate": False,
        "approval_level": "L2",  # Requires L2 Support review
        "description": "Data mutations require L2 Support Manager approval",
    },
    "UNKNOWN": {
        "auto_remediate": False,
        "approval_level": "L1",  # Escalate to L1
        "description": "Unknown issues are escalated to L1 for manual triage",
    },
}


def get_approval_requirement(issue_type: str) -> Dict[str, Any]:
    """Returns the RBAC rule for a given issue type."""
    return RBAC_RULES.get(issue_type, RBAC_RULES["UNKNOWN"])


def can_auto_remediate(issue_type: str) -> bool:
    """Check if an issue type allows automatic remediation."""
    rule = get_approval_requirement(issue_type)
    return rule.get("auto_remediate", False)


def get_approval_level(issue_type: str) -> str:
    """Returns the required approval level (L1, L2, L3, or None)."""
    rule = get_approval_requirement(issue_type)
    return rule.get("approval_level")
