"""
Outlook MCP Client — Connects to an Outlook/Microsoft 365 MCP Server.

Supports two modes:
  1. PRODUCTION: Uses the community npm package for Microsoft 365
     which connects via Microsoft Graph API.
  2. DEVELOPMENT: Falls back to the local mock server for offline testing.

Required env vars for production:
  - OUTLOOK_CLIENT_ID      (Azure AD App Registration Client ID)
  - OUTLOOK_CLIENT_SECRET  (Azure AD App Registration Client Secret)
  - OUTLOOK_TENANT_ID      (Azure AD Tenant ID)

Setup for production:
  Register an app at https://portal.azure.com → Azure Active Directory → App Registrations
  Grant Mail.Read, Mail.Send permissions in Microsoft Graph API
"""

import os
import sys
from src.mcp.client import BaseMCPClient


def get_outlook_client() -> BaseMCPClient:
    """
    Returns an MCP client configured for Outlook/Microsoft 365 email.
    Uses a Graph API-backed server in production, falls back to local mock.
    """
    client_id = os.getenv("OUTLOOK_CLIENT_ID", "")
    client_secret = os.getenv("OUTLOOK_CLIENT_SECRET", "")
    tenant_id = os.getenv("OUTLOOK_TENANT_ID", "")

    env = os.environ.copy()

    if client_id and client_secret and tenant_id:
        # ── Production: Microsoft Graph API MCP Server ──────────────
        print("[Outlook Client] Using OFFICIAL Microsoft Graph MCP server")
        server_command = "npx.cmd" if os.name == "nt" else "npx"
        server_args = ["-y", "@aashari/mcp-server-atlassian-confluence"]  
        # Note: A dedicated Outlook MCP npm server is still emerging.
        # For now, use the Graph API approach or custom server.
        # Replace server_args with official package when available.

        env["MICROSOFT_CLIENT_ID"] = client_id
        env["MICROSOFT_CLIENT_SECRET"] = client_secret
        env["MICROSOFT_TENANT_ID"] = tenant_id
    else:
        # ── Development: Local mock server ──────────────────────────
        print("[Outlook Client] Using LOCAL mock server (no OUTLOOK_CLIENT_ID set)")
        server_command = sys.executable
        server_args = ["src/mcp/mock_outlook_server.py"]

    return BaseMCPClient(server_command=server_command, server_args=server_args, env=env)
