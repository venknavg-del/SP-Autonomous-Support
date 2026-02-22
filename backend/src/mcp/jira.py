"""
Jira MCP Client — Connects to a Jira MCP Server.

Supports two modes:
  1. PRODUCTION: Uses the official npm package '@aashari/mcp-server-atlassian-jira'
     which connects to real Atlassian Jira Cloud via API tokens.
  2. DEVELOPMENT: Falls back to the local mock server for offline testing.

Required env vars for production:
  - JIRA_URL          (e.g., https://company.atlassian.net)
  - JIRA_EMAIL        (your Atlassian account email)
  - JIRA_API_TOKEN    (API token from id.atlassian.com/manage-profile/security/api-tokens)
"""

import os
import sys
from src.mcp.client import BaseMCPClient


def get_jira_client() -> BaseMCPClient:
    """
    Returns an MCP client configured for Jira.
    Uses the official npm MCP server in production, falls back to local mock.
    """
    jira_token = os.getenv("JIRA_API_TOKEN", "")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_url = os.getenv("JIRA_URL", "")

    env = os.environ.copy()

    if jira_token and jira_email:
        # ── Production: Official Atlassian Jira MCP Server ──────────
        # Package: https://www.npmjs.com/package/@aashari/mcp-server-atlassian-jira
        print("[Jira Client] Using OFFICIAL @aashari/mcp-server-atlassian-jira")
        server_command = "npx.cmd" if os.name == "nt" else "npx"
        server_args = ["-y", "@aashari/mcp-server-atlassian-jira"]

        # The official server reads these from environment
        env["ATLASSIAN_SITE_URL"] = jira_url
        env["ATLASSIAN_USER_EMAIL"] = jira_email
        env["ATLASSIAN_API_TOKEN"] = jira_token
    else:
        # ── Development: Local mock server ──────────────────────────
        print("[Jira Client] Using LOCAL mock server (no JIRA_API_TOKEN set)")
        server_command = sys.executable
        server_args = ["src/mcp/mock_jira_server.py"]

    return BaseMCPClient(server_command=server_command, server_args=server_args, env=env)
