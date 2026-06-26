"""Morgan MCP module — Model Context Protocol integration."""

from __future__ import annotations

import logging
from typing import Any, List
from langchain_core.tools import StructuredTool

logger = logging.getLogger("morgan.mcp")

class MCPServer:
    """Represents a connection to an external MCP server."""
    
    def __init__(self, name: str, command: str, args: list[str]) -> None:
        self.name = name
        self.command = command
        self.args = args
        self._tools: List[StructuredTool] = []

    async def connect(self) -> None:
        """Connect to the MCP server via stdio or HTTP (mock implementation)."""
        logger.info("Connecting to MCP server '%s' via %s %s", self.name, self.command, self.args)
        # In a real implementation, this would establish JSON-RPC over stdio
        self._tools = []

    def get_tools(self) -> List[StructuredTool]:
        """Return the tools exposed by this MCP server."""
        return self._tools

class MCPManager:
    """Manages multiple MCP server connections."""
    
    def __init__(self) -> None:
        self.servers: dict[str, MCPServer] = {}

    def register_server(self, name: str, command: str, args: list[str]) -> None:
        self.servers[name] = MCPServer(name, command, args)

    async def load_all_tools(self) -> List[StructuredTool]:
        """Connect to all servers and aggregate their tools."""
        all_tools = []
        for server in self.servers.values():
            try:
                await server.connect()
                all_tools.extend(server.get_tools())
            except Exception as e:
                logger.error("Failed to load tools from MCP server %s: %s", server.name, e)
        return all_tools
