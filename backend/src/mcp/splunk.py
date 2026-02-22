"""
Splunk MCP Client — Connects to a Splunk MCP Server.

Supports two modes:
  1. PRODUCTION: Uses the community 'splunk-mcp' server (livehybrid/splunk-mcp)
     which connects to real Splunk Enterprise/Cloud via REST API.
  2. DEVELOPMENT: Falls back to the local mock server for offline testing.

Required env vars for production:
  - SPLUNK_URL        (e.g., https://localhost:8089)
  - SPLUNK_API_KEY    (Splunk authentication token)
  - SPLUNK_APP        (optional, defaults to 'search')

Setup for production:
  pip install splunk-mcp  OR  git clone https://github.com/livehybrid/splunk-mcp
"""

import os
import sys
from src.mcp.client import BaseMCPClient


def get_splunk_client() -> BaseMCPClient:
    """
    Returns an MCP client configured for Splunk.
    Uses the community splunk-mcp server in production, falls back to local mock.
    """
    splunk_url = os.getenv("SPLUNK_URL", "")
    splunk_token = os.getenv("SPLUNK_API_KEY", "")

    env = os.environ.copy()

    if splunk_url and splunk_token:
        # ── Production: Community Splunk MCP Server ─────────────────
        # Package: https://github.com/livehybrid/splunk-mcp
        print("[Splunk Client] Using OFFICIAL splunk-mcp server")
        server_command = sys.executable
        server_args = ["-m", "splunk_mcp"]

        # The splunk-mcp server reads these from environment
        env["SPLUNK_URL"] = splunk_url
        env["SPLUNK_TOKEN"] = splunk_token
        env["SPLUNK_APP"] = os.getenv("SPLUNK_APP", "search")
        env["SPLUNK_VERIFY_SSL"] = os.getenv("SPLUNK_VERIFY_SSL", "false")
    else:
        # ── Development: Local mock server ──────────────────────────
        print("[Splunk Client] Using LOCAL mock server (no SPLUNK_API_KEY set)")
        server_command = sys.executable
        server_args = ["src/mcp/mock_splunk_server.py"]

    return BaseMCPClient(server_command=server_command, server_args=server_args, env=env)
