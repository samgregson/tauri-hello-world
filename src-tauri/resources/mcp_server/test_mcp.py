import sys
import json
import asyncio
from server import mcp

async def test_tool(tool_name, kwargs):
    try:
        # Execute it
        result = await mcp.call_tool(tool_name, kwargs)
        
        if hasattr(result, "model_dump"):
            result_data = result.model_dump()
        elif hasattr(result, "dict"):
            result_data = result.dict()
        else:
            result_data = str(result)
            
        return {"result": result_data}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        tools = mcp.list_tools()
        # FastMCP 3.x list_tools returns a list of tools directly or awaited
        if asyncio.iscoroutine(tools):
            tools = asyncio.run(tools)
        print(json.dumps({
            "tools": [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "schema": getattr(t, "parameters", {})
                }
                for t in tools
            ]
        }))
    else:
        tool_name = sys.argv[1]
        kwargs = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = asyncio.run(test_tool(tool_name, kwargs))
        print(json.dumps(result))
