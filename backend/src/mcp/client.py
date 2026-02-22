"""
Base MCP Client — Handles connection lifecycle, retries, and tool execution.
Includes retry with exponential backoff and circuit breaker pattern.
"""

import asyncio
import contextlib
import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("mcp.client")

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds
CIRCUIT_BREAKER_THRESHOLD = 5  # failures before circuit opens
CIRCUIT_BREAKER_RESET = 60  # seconds before circuit resets


class BaseMCPClient:
    """
    Base client for integrating with Model Context Protocol (MCP) servers.
    Includes retry logic and circuit breaker pattern.
    """
    def __init__(self, server_command: str, server_args: List[str], env: Optional[Dict[str, str]] = None):
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env=env
        )
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_open = False
        self._circuit_open_time: Optional[float] = None

    async def connect(self):
        """Connects to the MCP Server over stdio with retry logic."""
        if self._circuit_open:
            elapsed = asyncio.get_event_loop().time() - (self._circuit_open_time or 0)
            if elapsed < CIRCUIT_BREAKER_RESET:
                raise RuntimeError(f"Circuit breaker OPEN — too many failures. Resets in {CIRCUIT_BREAKER_RESET - elapsed:.0f}s")
            else:
                logger.info("Circuit breaker RESET — attempting reconnection")
                self._circuit_open = False
                self._failure_count = 0

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._exit_stack = contextlib.AsyncExitStack()
                read, write = await self._exit_stack.enter_async_context(stdio_client(self.server_params))
                self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                await self.session.initialize()
                self._failure_count = 0  # Reset on success
                logger.info(f"Connected to MCP Server: {self.server_params.command} (attempt {attempt})")
                return
            except Exception as e:
                last_error = e
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Connection attempt {attempt}/{MAX_RETRIES} failed: {e}. Retrying in {wait:.1f}s...")
                if self._exit_stack:
                    try:
                        await self._exit_stack.aclose()
                    except Exception:
                        pass
                await asyncio.sleep(wait)

        # All retries exhausted
        self._failure_count += 1
        if self._failure_count >= CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open = True
            self._circuit_open_time = asyncio.get_event_loop().time()
            logger.error(f"Circuit breaker OPENED after {self._failure_count} failures")
        raise ConnectionError(f"Failed to connect after {MAX_RETRIES} attempts: {last_error}")

    async def disconnect(self):
        """Disconnects the session gracefully."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
                logger.info("Disconnected from MCP Server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

    async def get_available_tools(self) -> List[Any]:
        """Lists tools available on this MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP Server")
        response = await self.session.list_tools()
        return response.tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Executes a tool with retry logic for transient errors."""
        if not self.session:
            raise RuntimeError("Not connected to MCP Server")

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Executing {tool_name}({arguments}) — attempt {attempt}")
                result = await self.session.call_tool(tool_name, arguments)
                return result
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(f"Tool {tool_name} failed (attempt {attempt}): {e}. Retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)

        logger.error(f"Tool {tool_name} failed after {MAX_RETRIES} attempts: {last_error}")
        raise last_error
