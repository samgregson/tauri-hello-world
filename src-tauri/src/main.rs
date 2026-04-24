// src-tauri/src/main.rs
//
// Entry point for the Tauri binary.
//
// Modes:
//   (no args)         → launch the normal GUI window
//   --mcp-server      → run as an MCP stdio server (JSON-RPC 2.0)
//                       This mode is used by Claude Desktop and other MCP hosts.
//
// MCP client config example (claude_desktop_config.json):
//   {
//     "mcpServers": {
//       "engineering-tools": {
//         "command": "C:\\...\\tauri-hello-world.exe",
//         "args": ["--mcp-server"]
//       }
//     }
//   }

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|a| a == "--mcp-server") {
        // stdio MCP server mode — no window, no Tauri runtime
        tauri_hello_world_lib::run_mcp_server();
    } else if args.iter().any(|a| a == "--setup-python") {
        // Dev helper to pre-create the Python venv
        tauri_hello_world_lib::setup_python_cli();
    } else {
        // Normal GUI mode
        tauri_hello_world_lib::run();
    }
}
