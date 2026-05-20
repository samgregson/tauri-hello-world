import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

function App() {
  const [greetMsg, setGreetMsg] = useState("Loading...");
  const [connected, setConnected] = useState(false);
  const [tools, setTools] = useState<string[]>([]);
  const [selectedTool, setSelectedTool] = useState("");
  const [toolArgs, setToolArgs] = useState("{}");
  const [toolResult, setToolResult] = useState("");

  async function checkBackend() {
    try {
      const msg = await invoke<string>("call_python_hello");
      setGreetMsg(msg);
      setConnected(true);
      fetchTools();
    } catch (error) {
      setGreetMsg("Error: Failed to invoke Python engine. " + String(error));
      setConnected(false);
    }
  }

  async function fetchTools() {
    try {
      const result = await invoke<string>("get_mcp_tools");
      const parsed = JSON.parse(result);
      if (parsed.tools) {
        setTools(parsed.tools);
        if (parsed.tools.length > 0) setSelectedTool(parsed.tools[0]);
      }
    } catch (error) {
      console.error("Failed to fetch tools", error);
    }
  }

  async function runTool() {
    setToolResult("Running...");
    try {
      const result = await invoke<string>("test_mcp_tool", { 
        toolName: selectedTool, 
        argsJson: toolArgs 
      });
      setToolResult(result);
    } catch (error) {
      setToolResult("Error: " + String(error));
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  return (
    <main className="container" style={{ padding: "2rem", fontFamily: "sans-serif", backgroundColor: "#0f0f13", minHeight: "100vh", color: "#ffffff", maxWidth: "800px", margin: "0 auto" }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "0.5rem", color: "#89b4fa", textAlign: "center" }}>Tauri + PyO3</h1>
      <p style={{ opacity: 0.7, marginBottom: "2rem", textAlign: "center" }}>Integrated Structural Engineering Tools</p>
      
      <div style={{ backgroundColor: "#1e1e2e", padding: "1.5rem", borderRadius: "12px", border: "1px solid #313244", color: "#cdd6f4", marginBottom: "2rem" }}>
        <h3 style={{ margin: "0 0 1rem 0", color: "#a6adc8" }}>Python Engine Status</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
           <div style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: connected ? "#a6e3a1" : "#f38ba8" }}></div>
           <p style={{ fontWeight: "bold", margin: 0 }}>{greetMsg}</p>
        </div>
      </div>

      <div style={{ backgroundColor: "#1e1e2e", padding: "1.5rem", borderRadius: "12px", border: "1px solid #313244", color: "#cdd6f4", marginBottom: "2rem" }}>
        <h3 style={{ margin: "0 0 1rem 0", color: "#a6adc8" }}>Test MCP Logic</h3>
        <div style={{ display: "flex", gap: "10px", marginBottom: "1rem" }}>
          <select 
            value={selectedTool} 
            onChange={e => setSelectedTool(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: "4px", backgroundColor: "#313244", color: "white", border: "none" }}
          >
            {tools.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input 
            type="text" 
            value={toolArgs} 
            onChange={e => setToolArgs(e.target.value)} 
            placeholder='{"arg": "value"}'
            style={{ flex: 1, padding: "0.5rem", borderRadius: "4px", backgroundColor: "#313244", color: "white", border: "none", fontFamily: "monospace" }}
          />
          <button 
            onClick={runTool}
            style={{ padding: "0.5rem 1rem", cursor: "pointer", borderRadius: "8px", backgroundColor: "#89b4fa", border: "none", color: "#11111b", fontWeight: "bold" }}
          >
            Run Tool
          </button>
        </div>
        <pre style={{ backgroundColor: "#11111b", padding: "1rem", borderRadius: "8px", overflowX: "auto", margin: 0 }}>
          {toolResult || "Select a tool and click Run."}
        </pre>
      </div>

      <div style={{ backgroundColor: "#1e1e2e", padding: "1.5rem", borderRadius: "12px", border: "1px solid #313244", color: "#cdd6f4" }}>
        <h3 style={{ margin: "0 0 1rem 0", color: "#a6adc8" }}>MCP Integration Instructions</h3>
        <p style={{ opacity: 0.9 }}>To use this MCP server in Claude Desktop, Cursor, or other MCP clients, configure them to run this executable with the <code>--mcp-server</code> flag.</p>
        
        <h4 style={{ color: "#89b4fa", marginTop: "1rem" }}>Claude Desktop (claude_desktop_config.json)</h4>
        <pre style={{ backgroundColor: "#11111b", padding: "1rem", borderRadius: "8px", overflowX: "auto", fontSize: "0.85rem" }}>
{`{
  "mcpServers": {
    "engineering-tools": {
      "command": "C:\\\\Program Files\\\\tauri-hello-world\\\\tauri-hello-world.exe",
      "args": ["--mcp-server"]
    }
  }
}`}
        </pre>
        <p style={{ fontSize: "0.85rem", opacity: 0.7, marginTop: "0.5rem" }}>
          * Adjust the path to match where the app is installed.
        </p>

        <h4 style={{ color: "#89b4fa", marginTop: "1rem" }}>FastAPI / SSE mode (For Custom Apps)</h4>
        <p style={{ fontSize: "0.85rem", opacity: 0.9 }}>
          If you want to integrate via HTTP (Server-Sent Events) in your own applications, run the executable manually or via a script with:
        </p>
        <pre style={{ backgroundColor: "#11111b", padding: "0.5rem 1rem", borderRadius: "8px", fontSize: "0.85rem" }}>
tauri-hello-world.exe --mcp-server --sse
        </pre>
        <p style={{ fontSize: "0.85rem", opacity: 0.9 }}>
          This will start an SSE endpoint on <code>http://127.0.0.1:8000/sse</code>.
        </p>
      </div>
    </main>
  );
}

export default App;
