# core/session.py

import os
import sys
import asyncio
import aiohttp
from typing import Optional, Any, List, Dict
from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
import json


class MCP:
    """
    Lightweight wrapper for one-time MCP tool calls using stdio transport.
    Each call spins up a new subprocess and terminates cleanly.
    """

    def __init__(
        self,
        server_script: str = "mcp_server_2.py",
        working_dir: Optional[str] = None,
        server_command: Optional[str] = None,
    ):
        self.server_script = server_script
        self.working_dir = working_dir or os.getcwd()
        self.server_command = server_command or sys.executable

    async def list_tools(self):
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return tools_result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)


class MultiMCP:
    """
    Stateless version: discovers tools from multiple MCP servers, but reconnects per tool call.
    Each call_tool() uses a fresh session based on tool-to-server mapping.
    """

    def __init__(self, server_configs: List[dict]):
        self.server_configs = server_configs
        self.tool_map: Dict[str, Dict[str, Any]] = {}  # tool_name → {config, tool}
        self.sse_clients: Dict[str, aiohttp.ClientSession] = {}  # server_name → client

    async def initialize(self):
        print("in MultiMCP initialize")
        for config in self.server_configs:
            try:
                if config.get("transport") == "sse":
                    # Initialize SSE client for this server
                    self.sse_clients[config["name"]] = aiohttp.ClientSession()
                    print(f"→ Initialized SSE client for: {config['name']}")
                    
                    # Add tools for SSE server
                    tools = [
                        Tool(
                            name="send_question",
                            description="Send a question to Telegram",
                            inputSchema={
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "The question to send"
                                    }
                                },
                                "required": ["question"]
                            }
                        ),
                        Tool(
                            name="send_acknowledgement",
                            description="Send an acknowledgement to Telegram",
                            inputSchema={
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "The message to send"
                                    }
                                },
                                "required": ["message"]
                            }
                        )
                    ]
                    
                    for tool in tools:
                        self.tool_map[tool.name] = {
                            "config": config,
                            "tool": tool
                        }
                        print(f"→ Registered tool: {tool.name} for server: {config['name']}")
                    continue

                params = StdioServerParameters(
                    command=sys.executable,
                    args=[config["script"]],
                    cwd=config.get("cwd", os.getcwd())
                )
                print(f"→ Scanning tools from: {config['script']} in {params.cwd}")
                async with stdio_client(params) as (read, write):
                    print("Connection established, creating session...")
                    try:
                        async with ClientSession(read, write) as session:
                            print("[agent] Session created, initializing...")
                            await session.initialize()
                            print("[agent] MCP session initialized")
                            tools = await session.list_tools()
                            print(f"→ Tools received: {[tool.name for tool in tools.tools]}")
                            for tool in tools.tools:
                                self.tool_map[tool.name] = {
                                    "config": config,
                                    "tool": tool
                                }
                                print(f"→ Registered tool: {tool.name} for server: {config['script']}")
                    except Exception as se:
                        print(f"❌ Session error: {se}")
            except Exception as e:
                print(f"❌ Error initializing MCP server {config['script']}: {e}")

        # Print all registered tools
        print("\nRegistered tools:")
        for tool_name, entry in self.tool_map.items():
            print(f"→ {tool_name} on {entry['config'].get('name', entry['config'].get('script', 'unknown'))}")

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        entry = self.tool_map.get(tool_name)
        if not entry:
            raise ValueError(f"Tool '{tool_name}' not found on any server.")

        config = entry["config"]
        
        if config.get("transport") == "sse":
            # Handle SSE transport
            server_name = config["name"]
            endpoint = config["endpoints"].get(tool_name)
            if not endpoint:
                raise ValueError(f"Endpoint not found for tool '{tool_name}'")
            
            url = f"{config['url']}{endpoint}"
            print(f"→ Calling SSE tool {tool_name} at {url}")
            async with self.sse_clients[server_name] as session:
                async with session.post(url, json=arguments) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}: {await response.text()}")
                    return await response.json()

        # Handle stdio transport
        params = StdioServerParameters(
            command=sys.executable,
            args=[config["script"]],
            cwd=config.get("cwd", os.getcwd())
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)

    async def list_all_tools(self) -> List[str]:
        return list(self.tool_map.keys())

    def get_all_tools(self) -> List[Any]:
        return [entry["tool"] for entry in self.tool_map.values()]

    async def shutdown(self):
        # Close all SSE clients
        for client in self.sse_clients.values():
            await client.close()