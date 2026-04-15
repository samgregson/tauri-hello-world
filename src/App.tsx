import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [greetMsg, setGreetMsg] = useState("Loading...");
  const [connected, setConnected] = useState(false);

  async function checkBackend() {
    try {
      const response = await fetch("http://127.0.0.1:8000/hello");
      const data = await response.json();
      setGreetMsg(`Success: ${data.message}`);
      setConnected(true);
    } catch (error) {
      setGreetMsg("Error: Failed to connect to FastAPI backend. " + String(error));
      setConnected(false);
    }
  }

  useEffect(() => {
    checkBackend(); // Try immediately

    const interval = setInterval(() => {
      if (!connected) {
        checkBackend();
      }
    }, 300);

    return () => clearInterval(interval);
  }, [connected]);

  return (
    <main className="container" style={{ padding: "2rem", textAlign: "center", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "1rem" }}>Tauri + React + FastAPI</h1>
      <div style={{ backgroundColor: "#1e1e2e", padding: "1.5rem", borderRadius: "8px", color: "#cdd6f4", marginTop: "2rem", display: "inline-block" }}>
        <h3>Backend Status</h3>
        <p style={{ fontWeight: "bold", marginTop: "1rem" }}>{greetMsg}</p>
      </div>
      <div style={{ marginTop: "2rem" }}>
        <button onClick={checkBackend} style={{ padding: "0.5rem 1rem", cursor: "pointer", borderRadius: "4px", backgroundColor: "#89b4fa", border: "none", color: "#11111b", fontWeight: "bold" }}>
          Ping Backend Manually
        </button>
      </div>
    </main>
  );
}

export default App;
