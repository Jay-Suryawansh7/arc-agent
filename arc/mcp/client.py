"""
MCP Client Manager.
Manages connections to multiple MCP servers (stdio transport).
"""
import logging
import asyncio
from typing import Dict, List, Optional
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from contextlib import AsyncExitStack

from arc.config import get_config, MCPServerConfig

logger = logging.getLogger(__name__)

class MCPClientManager:
    def __init__(self):
        self.config = get_config()
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self._tool_cache: Dict[str, List] = {}

    async def start(self):
        """
        Start all enabled MCP servers.
        """
        logger.info("Starting MCP Client Manager...")
        
        servers = self.config.mcp.servers
        for name, server_config in servers.items():
            if server_config.enabled:
                try:
                    await self.connect_server(name, server_config)
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server '{name}': {e}")
            else:
                logger.info(f"MCP Server '{name}' is disabled.")

    async def connect_server(self, name: str, config: MCPServerConfig):
        """
        Connect to a specific MCP server using stdio transport.
        """
        logger.info(f"Connecting to server: {name} ({config.command} {config.args})")
        
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env={**config.env} # Add custom env vars if needed
        )

        try:
            # We use the exit stack to manage the context managers for read/write streams and session
            # This is a bit complex because stdio_client returns a context manager that yields (read, write)
            # and ClientSession is also an async context manager.
            
            # Note: In a real long-running app, we need to handle the lifecycle carefully.
            # Here we might need to hold onto the context managers.
            
            # Using the low-level connect pattern for better control
            transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            read, write = transport
            
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            await session.initialize()
            self.sessions[name] = session
            logger.info(f"Connected to MCP server: {name}")
            
            # Cache tools immediately
            tools_result = await session.list_tools()
            self._tool_cache[name] = tools_result.tools
            
        except Exception as e:
            logger.error(f"Connection error for {name}: {e}")
            raise

    async def stop(self):
        """
        Stop all servers and cleanup.
        """
        logger.info("Stopping MCP Client Manager...")
        await self.exit_stack.aclose()
        self.sessions.clear()
        self._tool_cache.clear()

    async def restart_server(self, name: str):
        """
        Restart a specific server (not fully supported with single ExitStack yet, 
        would require separate stacks per server in robust implementation).
        For now, this is a placeholder or would require refactoring to individual stacks.
        """
        logger.warning(f"Restarting {name} not fully implemented in this simple manager.")
        pass

    def get_all_tools(self) -> List[dict]:
        """
        Get combined list of tools from all connected servers.
        Returns a simplified list of tool descriptions.
        """
        all_tools = []
        for server_name, tools in self._tool_cache.items():
            for tool in tools:
                # Add server prefix or metadata if needed?
                # For now just return the tool object
                all_tools.append(tool)
        return all_tools

    def get_tools_by_server(self, name: str) -> List:
        return self._tool_cache.get(name, [])

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        """
        Call a tool on a specific server.
        If server_name is not known, we might need to search for the tool.
        """
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")
        
        return await session.call_tool(tool_name, arguments)
    
    async def find_and_call_tool(self, tool_name: str, arguments: dict):
        """
        Find which server has the tool and call it.
        """
        for name, tools in self._tool_cache.items():
            for tool in tools:
                if tool.name == tool_name:
                    return await self.call_tool(name, tool_name, arguments)
        raise ValueError(f"Tool {tool_name} not found in any connected server")

# Singleton instance management could go here or in a separate container
_mcp_manager: Optional[MCPClientManager] = None

def get_mcp_manager() -> MCPClientManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager
