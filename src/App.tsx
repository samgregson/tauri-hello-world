import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

function App() {
  const [greetMsg, setGreetMsg] = useState("Loading...");
  const [connected, setConnected] = useState(false);

  async function checkBackend() {
    try {
      const msg = await invoke<string>("call_python_hello");
      setGreetMsg(msg);
      setConnected(true);
    } catch (error) {
      setGreetMsg("Error: Failed to invoke Python engine. " + String(error));
      setConnected(false);
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  return (
    <main className="container" style={{ padding: "2rem", textAlign: "center", fontFamily: "sans-serif", backgroundColor: "#0f0f13", minHeight: "100vh", color: "#ffffff" }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "0.5rem", color: "#89b4fa" }}>Tauri + PyO3</h1>
      <p style={{ opacity: 0.7, marginBottom: "2rem" }}>Integrated Structural Engineering Tools</p>
      
      <div style={{ backgroundColor: "#1e1e2e", padding: "1.5rem", borderRadius: "12px", border: "1px solid #313244", color: "#cdd6f4", marginTop: "1rem", display: "inline-block", minWidth: "300px" }}>
        <h3 style={{ margin: "0 0 1rem 0", color: "#a6adc8" }}>Python Engine Status</h3>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "10px" }}>
           <div style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: connected ? "#a6e3a1" : "#f38ba8" }}></div>
           <p style={{ fontWeight: "bold", margin: 0 }}>{greetMsg}</p>
        </div>
      </div>

      <div style={{ marginTop: "2.5rem", display: "flex", gap: "10px", justifyContent: "center" }}>
        <button 
          onClick={checkBackend} 
          style={{ padding: "0.75rem 1.5rem", cursor: "pointer", borderRadius: "8px", backgroundColor: "#89b4fa", border: "none", color: "#11111b", fontWeight: "bold", transition: "transform 0.1s" }}
          onMouseDown={(e) => e.currentTarget.style.transform = "scale(0.95)"}
          onMouseUp={(e) => e.currentTarget.style.transform = "scale(1)"}
        >
          Check Python
        </button>
      </div>
      
      <div style={{ marginTop: "4rem", fontSize: "0.8rem", color: "#6c7086" }}>
        <p>This app runs an <b>in-process</b> Python interpreter for MCP tools and COM automation.</p>
        <p>No external backend process is required.</p>
      </div>
    </main>
  );
}

export default App;
