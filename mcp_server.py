"""NOVA's tools as an MCP server, so any MCP client (Claude Code, Claude Desktop,
other agents) can use them.

It reuses the registry in tools.py: the menu comes from TOOLS and every call
goes through tools.run_tool - the same two pieces the agent loop uses. MCP only
changes who is asking.

Run by an MCP client over stdio, e.g. in Claude Code:
    claude mcp add nova -- D:\\nova\\venv\\Scripts\\python.exe D:\\nova\\mcp_server.py
"""
import contextlib
import json
import sys

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

import config
import tools

# Not offered over MCP:
#   get_weather  - fake, only for learning
#   create_event - a write action whose safety depends on NOVA's own approval
#                  step (approvals.py), which an outside client does not go through
HIDDEN_TOOLS = {"get_weather", "create_event"}


def visible_tools():
    """The registry entries this server offers."""
    return {name: tool for name, tool in tools.TOOLS.items() if name not in HIDDEN_TOOLS}


async def list_tools(ctx, params):
    """Answer "what tools do you have?" - built from the same registry as tool_menu()."""
    return types.ListToolsResult(tools=[
        types.Tool(name=name, description=tool["description"], input_schema=tool["parameters"])
        for name, tool in visible_tools().items()
    ])


def run_quietly(name, arguments):
    """Run one tool, sending any print() output to stderr.

    MCP messages travel over stdout, so a stray print (e.g. Google's sign-in
    URL) would corrupt them.
    """
    with contextlib.redirect_stdout(sys.stderr):
        # The MCP server runs on the owner's own machine, like the terminal
        # chat, so it acts as the owner.
        return tools.run_tool(name, json.dumps(arguments or {}), config.MY_CHAT_ID)


async def call_tool(ctx, params):
    """Run the tool a client asked for and return its text."""
    if params.name not in visible_tools():
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Unknown tool: {params.name}")],
            is_error=True,
        )
    # Tools do slow network calls; a worker thread keeps the server responsive.
    result = await anyio.to_thread.run_sync(run_quietly, params.name, params.arguments)
    return types.CallToolResult(content=[types.TextContent(type="text", text=result)])


server = Server(
    "nova",
    version="1.0.0",
    instructions="NOVA's personal-assistant tools: time, web search, memory, Google Calendar (read) and Gmail (read, drafts).",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
