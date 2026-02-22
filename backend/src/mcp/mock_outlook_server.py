"""
Outlook MCP Server — Exposes email-related tools via FastMCP.

Tools:
  - search_emails: Search inbox by keyword/sender/date
  - get_email: Fetch a specific email by ID
  - send_email: Send an email (for auto-notification workflows)

In production, replace mock logic with Microsoft Graph API calls.
Requires: OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET, OUTLOOK_TENANT_ID
"""

from mcp.server.fastmcp import FastMCP
import json
import os
from datetime import datetime

mcp = FastMCP("Outlook Email Server")


@mcp.tool()
def search_emails(query: str, folder: str = "inbox", max_results: int = 5) -> str:
    """
    Searches the user's mailbox for emails matching a keyword query.
    Returns a JSON array of email summaries.
    """
    # Production: Use Microsoft Graph API
    # GET https://graph.microsoft.com/v1.0/me/messages?$search="query"
    
    mock_emails = [
        {
            "id": "MSG-001",
            "subject": "URGENT: Payment Gateway 500 errors spiking",
            "from": "alerts@monitoring.company.com",
            "date": "2024-05-20T09:55:00Z",
            "snippet": "Error rate on /checkout has exceeded 5% threshold. NullPointerException seen in PaymentService.",
            "has_attachments": True
        },
        {
            "id": "MSG-002",
            "subject": "RE: Database connection pool exhaustion",
            "from": "devops@company.com",
            "date": "2024-05-20T11:10:00Z",
            "snippet": "HikariPool-1 reporting connection timeout. Current pool utilization at 98%.",
            "has_attachments": False
        },
        {
            "id": "MSG-003",
            "subject": "Weekly Incident Summary - Sprint 42",
            "from": "support-lead@company.com",
            "date": "2024-05-19T16:00:00Z",
            "snippet": "3 P1 incidents this week. Root causes: 2 code bugs, 1 infra misconfiguration.",
            "has_attachments": True
        }
    ]
    
    # Filter by keyword
    results = [e for e in mock_emails if query.lower() in e["subject"].lower() 
               or query.lower() in e["snippet"].lower()]
    
    if not results:
        results = mock_emails[:max_results]
    
    return json.dumps(results[:max_results], indent=2)


@mcp.tool()
def get_email(email_id: str) -> str:
    """
    Fetches the full content of a specific email by its ID.
    Returns the complete email body, headers, and attachment metadata.
    """
    # Production: GET https://graph.microsoft.com/v1.0/me/messages/{email_id}
    
    mock_full_emails = {
        "MSG-001": {
            "id": "MSG-001",
            "subject": "URGENT: Payment Gateway 500 errors spiking",
            "from": "alerts@monitoring.company.com",
            "to": ["oncall-l1@company.com", "oncall-l2@company.com"],
            "date": "2024-05-20T09:55:00Z",
            "body": (
                "Hi Team,\n\n"
                "We are seeing a massive spike in 500 errors on the /checkout endpoint.\n"
                "Splunk dashboard shows 500+ NullPointerExceptions in the last 10 minutes.\n"
                "Stack trace points to PaymentService.java line 145.\n\n"
                "Affected customers cannot complete orders. Revenue impact estimated at $50K/hr.\n\n"
                "Please investigate immediately.\n\n"
                "- Monitoring Bot"
            ),
            "attachments": [
                {"name": "error_rate_chart.png", "size_kb": 245, "content_type": "image/png"}
            ]
        },
        "MSG-002": {
            "id": "MSG-002",
            "subject": "RE: Database connection pool exhaustion",
            "from": "devops@company.com",
            "to": ["oncall-l1@company.com"],
            "date": "2024-05-20T11:10:00Z",
            "body": (
                "Team,\n\n"
                "HikariPool-1 is reporting connection timeouts.\n"
                "Active connections: 100/100 (max reached).\n"
                "Idle connections: 0.\n\n"
                "The auto-scale terraform rule did not trigger because the threshold\n"
                "was set to 95% for 30 minutes, but we hit 100% in 15 minutes.\n\n"
                "Recommend increasing pool to 150 immediately.\n\n"
                "- DevOps Team"
            ),
            "attachments": []
        }
    }
    
    email = mock_full_emails.get(email_id)
    if email:
        return json.dumps(email, indent=2)
    return json.dumps({"error": f"Email {email_id} not found"})


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """
    Sends an email notification. Used by the Resolution Agent to notify
    stakeholders about automated fixes or escalations.
    """
    # Production: POST https://graph.microsoft.com/v1.0/me/sendMail
    
    print(f"[Outlook MCP] Sending email to {to}: {subject}")
    return json.dumps({
        "status": "sent",
        "message_id": f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "to": to,
        "subject": subject,
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    mcp.run()
