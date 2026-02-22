"""
Jira MCP Server — Exposes ticket management tools via FastMCP.

Tools:
  - search_tickets: Search Jira tickets by JQL query
  - get_ticket: Fetch full ticket details by key
  - create_ticket: Create a new incident ticket
  - add_comment: Add a comment/update to an existing ticket
  - transition_ticket: Move ticket status (e.g., Open → In Progress → Resolved)

In production, replace mock logic with Jira REST API calls.
Requires: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
"""

from mcp.server.fastmcp import FastMCP
import json
from datetime import datetime

mcp = FastMCP("Jira Ticket Server")


# ─── Mock Data ────────────────────────────────────────────────────────

MOCK_TICKETS = {
    "SP-301": {
        "key": "SP-301",
        "summary": "NullPointerException in PaymentService causing checkout failures",
        "status": "Open",
        "priority": "P1 - Critical",
        "assignee": "dev-oncall@company.com",
        "reporter": "monitoring-bot@company.com",
        "created": "2024-05-20T09:58:00Z",
        "labels": ["payment", "production", "bug"],
        "description": (
            "500+ NullPointerException errors in PaymentService.java:145.\n"
            "Users unable to complete checkout. Revenue impact ~$50K/hr.\n"
            "Stack trace indicates user.getBalance() returns null when wallet is empty."
        ),
        "comments": [
            {"author": "triage-bot", "body": "Auto-classified as P1. Escalated to L2.", "created": "2024-05-20T10:00:00Z"},
            {"author": "dev-oncall", "body": "Investigating. Looks like a missing null check.", "created": "2024-05-20T10:15:00Z"}
        ]
    },
    "SP-302": {
        "key": "SP-302",
        "summary": "Database connection pool exhaustion - HikariPool timeout",
        "status": "In Progress",
        "priority": "P2 - High",
        "assignee": "devops-oncall@company.com",
        "reporter": "splunk-alert@company.com",
        "created": "2024-05-20T11:12:00Z",
        "labels": ["infrastructure", "database", "production"],
        "description": (
            "HikariPool-1 reporting connection timeouts.\n"
            "Active connections: 100/100 (pool exhausted).\n"
            "Auto-scale rule did not trigger (threshold: 95% for 30min, hit 100% in 15min)."
        ),
        "comments": [
            {"author": "triage-bot", "body": "Auto-classified as P2. Infra issue detected.", "created": "2024-05-20T11:15:00Z"}
        ]
    },
    "SP-101": {
        "key": "SP-101",
        "summary": "Historical: NullPointerException in PaymentService during checkout",
        "status": "Resolved",
        "priority": "P1 - Critical",
        "assignee": "senior-dev@company.com",
        "reporter": "monitoring-bot@company.com",
        "created": "2024-04-10T14:30:00Z",
        "labels": ["payment", "production", "bug", "resolved"],
        "description": "Similar NPE in PaymentService. Fixed by adding null check for user balance.",
        "comments": [
            {"author": "senior-dev", "body": "Root cause: missing null guard. PR #4052 merged.", "created": "2024-04-10T16:45:00Z"}
        ]
    }
}


# ─── Tools ────────────────────────────────────────────────────────────

@mcp.tool()
def search_tickets(jql: str, max_results: int = 10) -> str:
    """
    Searches Jira tickets using JQL (Jira Query Language).
    Example JQL: 'project = SP AND status = Open AND priority = P1'
    Returns a JSON array of matching ticket summaries.
    """
    # Production: GET /rest/api/3/search?jql={jql}
    
    results = []
    jql_lower = jql.lower()
    
    for key, ticket in MOCK_TICKETS.items():
        # Simple keyword matching against JQL
        match = False
        if "open" in jql_lower and ticket["status"] == "Open":
            match = True
        elif "in progress" in jql_lower and ticket["status"] == "In Progress":
            match = True
        elif "resolved" in jql_lower and ticket["status"] == "Resolved":
            match = True
        elif "p1" in jql_lower and "P1" in ticket["priority"]:
            match = True
        elif "p2" in jql_lower and "P2" in ticket["priority"]:
            match = True
        elif "payment" in jql_lower and "payment" in ticket["labels"]:
            match = True
        elif "database" in jql_lower and "database" in ticket["labels"]:
            match = True
        
        # Fallback: match any keyword in summary
        if not match:
            for word in jql_lower.split():
                if word in ticket["summary"].lower():
                    match = True
                    break
        
        if match:
            results.append({
                "key": ticket["key"],
                "summary": ticket["summary"],
                "status": ticket["status"],
                "priority": ticket["priority"],
                "assignee": ticket["assignee"]
            })
    
    return json.dumps(results[:max_results], indent=2)


@mcp.tool()
def get_ticket(ticket_key: str) -> str:
    """
    Fetches the full details of a Jira ticket by its key (e.g., 'SP-301').
    Returns the complete ticket including description, comments, and metadata.
    """
    # Production: GET /rest/api/3/issue/{ticket_key}
    
    ticket = MOCK_TICKETS.get(ticket_key)
    if ticket:
        return json.dumps(ticket, indent=2)
    return json.dumps({"error": f"Ticket {ticket_key} not found"})


@mcp.tool()
def create_ticket(project: str, summary: str, description: str, priority: str = "P2") -> str:
    """
    Creates a new Jira ticket for the incident.
    Used by the Triage Agent to auto-create tickets for incoming alerts.
    """
    # Production: POST /rest/api/3/issue
    
    new_key = f"{project}-{len(MOCK_TICKETS) + 400}"
    new_ticket = {
        "key": new_key,
        "summary": summary,
        "description": description,
        "status": "Open",
        "priority": priority,
        "created": datetime.now().isoformat()
    }
    
    print(f"[Jira MCP] Created ticket: {new_key}")
    return json.dumps({"status": "created", "ticket": new_ticket}, indent=2)


@mcp.tool()
def add_comment(ticket_key: str, comment: str) -> str:
    """
    Adds a comment to an existing Jira ticket.
    Used by agents to log their analysis findings and actions taken.
    """
    # Production: POST /rest/api/3/issue/{ticket_key}/comment
    
    print(f"[Jira MCP] Adding comment to {ticket_key}: {comment[:80]}...")
    return json.dumps({
        "status": "added",
        "ticket_key": ticket_key,
        "comment_id": f"CMT-{datetime.now().strftime('%H%M%S')}",
        "timestamp": datetime.now().isoformat()
    })


@mcp.tool()
def transition_ticket(ticket_key: str, new_status: str) -> str:
    """
    Transitions a ticket to a new status (e.g., 'Open' → 'In Progress' → 'Resolved').
    Used by the Resolution Agent to update ticket status after applying fixes.
    """
    # Production: POST /rest/api/3/issue/{ticket_key}/transitions
    
    valid_statuses = ["Open", "In Progress", "Under Review", "Resolved", "Closed"]
    if new_status not in valid_statuses:
        return json.dumps({"error": f"Invalid status. Must be one of: {valid_statuses}"})
    
    print(f"[Jira MCP] Transitioning {ticket_key} → {new_status}")
    return json.dumps({
        "status": "transitioned",
        "ticket_key": ticket_key,
        "new_status": new_status,
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    mcp.run()
