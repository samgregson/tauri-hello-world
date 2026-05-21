import sys
import json
import asyncio
from server import mcp

async def test_tool(tool_name, kwargs):
    try:
        # Execute it
        result = await mcp.call_tool(tool_name, kwargs)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        tools = mcp.list_tools()
        # FastMCP 3.x list_tools returns a list of tools directly or awaited
        if asyncio.iscoroutine(tools):
            tools = asyncio.run(tools)
        print(json.dumps({"tools": [t.name for t in tools]}))
    else:
        tool_name = sys.argv[1]
        kwargs = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = asyncio.run(test_tool(tool_name, kwargs))
        print(json.dumps(result))
