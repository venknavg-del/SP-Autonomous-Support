import os
from src.mcp.client import BaseMCPClient

def get_github_client() -> BaseMCPClient:
    """
    Initializes an MCP Client connected to the GitHub MCP server.
    Uses npx to run the official @modelcontextprotocol/server-github.
    Requires GITHUB_PERSONAL_ACCESS_TOKEN in the environment.
    """
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    
    # Usually executed via npx on windows as 'npx.cmd'
    server_command = "npx.cmd" if os.name == "nt" else "npx"
    server_args = ["-y", "@modelcontextprotocol/server-github"]
    
    env = os.environ.copy()
    if github_token:
        # The MCP server specifically looks for this environment variable
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token
        
    return BaseMCPClient(server_command=server_command, server_args=server_args, env=env)
