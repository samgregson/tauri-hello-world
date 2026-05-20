import sys
import json
import asyncio
from server import mcp

async def test_tool(tool_name, kwargs):
    try:
        # Find the tool
        tool = next((t for t in mcp._tools.values() if t.name == tool_name), None)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found."}
        
        # Execute it
        result = await tool.fn(**kwargs)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"tools": [t.name for t in mcp._tools.values()]}))
    else:
        tool_name = sys.argv[1]
        kwargs = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = asyncio.run(test_tool(tool_name, kwargs))
        print(json.dumps(result))
