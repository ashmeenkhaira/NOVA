"""mcp_server.py handlers, called directly - no subprocess needed."""
import asyncio
from types import SimpleNamespace

import mcp_server


def test_lists_registry_tools_except_hidden_ones():
    result = asyncio.run(mcp_server.list_tools(None, None))
    names = {tool.name for tool in result.tools}
    assert "get_current_time" in names and "search_emails" in names
    assert names.isdisjoint(mcp_server.HIDDEN_TOOLS)


def test_call_tool_runs_through_the_registry():
    result = asyncio.run(mcp_server.call_tool(None, SimpleNamespace(name="get_current_time", arguments={})))
    assert not result.is_error
    assert result.content[0].text   # e.g. "Sunday, 04 October 2026, 04:53 PM"


def test_hidden_write_tool_is_refused():
    params = SimpleNamespace(name="create_event", arguments={"title": "x", "start": "2026-10-06T07:00", "end": "2026-10-06T08:00"})
    result = asyncio.run(mcp_server.call_tool(None, params))
    assert result.is_error
