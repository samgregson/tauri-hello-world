# Tauri + Embedded Python MCP Server — Architecture Plan

## Requirements recap

| Requirement | Implication |
|---|---|
| Self-contained (no system Python needed) | Must bundle CPython |
| Python logic (familiar) | PyO3 for in-process embedding |
| FastMCP for MCP protocol | Bundle fastmcp + its deps |
| COM automation (Windows app interactivity) | Must bundle pywin32 |
| No IT-blocked sidecar (no subprocess spawn of unknown binary) | Python must run **in-process** |

---

## The COM constraint is the deciding factor

`pywin32` (`win32com.client`) requires:
- **CPython on Windows** — no PyPy, no RustPython, no Wasm
- **Native DLLs** — `pythoncom3xx.dll`, `pywintypes3xx.dll` — these cannot be statically linked; they must exist as files

This rules out any approach that avoids files-on-disk entirely. "Self-contained" here means **bundled alongside the binary**, not a single-file binary.

---

## Three candidate approaches

### Approach A — PyO3 + python-build-standalone ✅ Recommended

**How it works:**
1. At build time, download Astral's `python-build-standalone` (a portable, relocatable CPython build) for the target platform
2. `pip install fastmcp pywin32 ...` into this bundled distribution
3. PyO3 in [Cargo.toml](file:///home/sam/.gemini/antigravity/scratch/tauri-hello-world/src-tauri/Cargo.toml) links against the bundled `python3xx.dll`/`libpython.so`
4. Tauri bundles the entire Python distribution as resources
5. At startup, Rust sets `PYTHONHOME` to the resource path and calls `pyo3::prepare_freethreaded_python()`
6. When invoked as an MCP server (`--mcp-server` flag), the FastMCP server runs via PyO3 — **in-process, no subprocess**

```
[MCP Host]
    │ stdin/stdout (JSON-RPC 2.0)
    ▼
[tauri-hello-world --mcp-server]    ← single signed binary
    │
    ├── Rust: stdio transport loop
    └── PyO3 → CPython (in-process)
                 └── FastMCP server
                       └── @mcp.tool()  →  win32com.client.Dispatch(...)
```

**Pros:**
- Python code runs **in-process** (no subprocess spawn)
- Write all MCP tools in Python with FastMCP decorators
- Full pywin32 COM access
- No system Python required — fully self-contained
- FastMCP handles all MCP protocol complexity

**Cons:**
- Build complexity: need build script to download python-build-standalone and pip install
- Bundle size: +30-60 MB for Python stdlib + packages
- pywin32 native DLLs (`pythoncomXX.dll`) live as separate files in the bundle (unavoidable)
- asyncio + PyO3 needs careful thread handling (`pyo3-async-runtimes` crate)

---

### Approach B — Full Rust MCP + `windows-rs` for COM ❌ Not recommended

Use the `windows` crate (Microsoft's official Rust COM bindings) for automation, implement MCP in Rust.

**Rejected because:** User prefers Python; COM automation in Rust via `windows-rs` requires writing verbose, unsafe COM code — much harder than `win32com.client.Dispatch("Excel.Application")`.

---

### Approach C — Bundled portable Python + subprocess (revisited) ⚠️ Fallback only

Bundle `python-build-standalone` as a Tauri resource, extract on first run, spawn it as a subprocess.

**Rejected as primary** because this still involves subprocess spawning (your IT restriction). However, if the IT restriction is specifically about **AV flagging PyInstaller-built binaries** (common!) rather than process spawn policy, this would work and is simpler to build. Worth clarifying with your IT team.

---

## Recommended implementation plan (Approach A)

### Phase 1: Strip the old sidecar

- Remove `externalBin` from [tauri.conf.json](file:///home/sam/.gemini/antigravity/scratch/tauri-hello-world/src-tauri/tauri.conf.json)
- Remove the Python sidecar spawn code from [lib.rs](file:///home/sam/.gemini/antigravity/scratch/tauri-hello-world/src-tauri/src/lib.rs)
- Remove `backend/` Python code and PyInstaller spec files
- Keep `tauri-plugin-shell` (useful for other things) or remove if not needed

### Phase 2: Set up embedded Python build

Create `scripts/setup-python.js` (or [.py](file:///home/sam/.gemini/antigravity/scratch/tauri-hello-world/backend/main.py)) that:
1. Downloads `python-build-standalone` for the current target triple (Windows/Linux/macOS)
2. Extracts it to `src-tauri/resources/python/`
3. Runs `pip install fastmcp pywin32 pywin32-ctypes` into that distribution

This runs as part of `npm run build` (add to `beforeBuildCommand`).

### Phase 3: PyO3 in Cargo.toml

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["auto-initialize"] }
pyo3-async-runtimes = { version = "0.23", features = ["tokio-runtime"] }
```

Set in [build.rs](file:///home/sam/.gemini/antigravity/scratch/tauri-hello-world/src-tauri/build.rs) (or `.cargo/config.toml`):
- `PYO3_PYTHON` = path to the bundled Python executable

### Phase 4: MCP entry point in main.rs

```rust
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.contains(&"--mcp-server".to_string()) {
        run_mcp_server();  // PyO3: runs FastMCP on stdin/stdout
    } else {
        tauri_hello_world_lib::run();  // Normal Tauri GUI
    }
}
```

### Phase 5: FastMCP server in Python (bundled resource)

```python
# src-tauri/resources/mcp_server/server.py
from fastmcp import FastMCP
import sys

mcp = FastMCP("MyApp MCP Server")

@mcp.tool()
def com_tool(app_name: str, method: str) -> str:
    """Control a COM application"""
    import win32com.client
    app = win32com.client.Dispatch(app_name)
    # ... your COM logic
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

The Rust `run_mcp_server()` function:
```rust
fn run_mcp_server() {
    // Set PYTHONHOME to bundled python
    let exe_dir = std::env::current_exe().unwrap().parent().unwrap().to_owned();
    std::env::set_var("PYTHONHOME", exe_dir.join("resources/python"));
    std::env::set_var("PYTHONPATH", exe_dir.join("resources/python/Lib")
        .to_str().unwrap().to_string()
        + ";" + exe_dir.join("resources/mcp_server").to_str().unwrap());

    pyo3::prepare_freethreaded_python();
    Python::with_gil(|py| {
        py.run("import server; server.mcp.run(transport='stdio')", None, None)
            .expect("MCP server failed");
    });
}
```

### Phase 6: MCP client config

Users configure their MCP client (Claude Desktop, etc.) as:
```json
{
  "mcpServers": {
    "myapp": {
      "command": "C:\\Users\\...\\tauri-hello-world.exe",
      "args": ["--mcp-server"]
    }
  }
}
```

---

## asyncio note

FastMCP uses asyncio. When running via PyO3 in-process, the event loop needs to be explicitly started. The call `mcp.run(transport="stdio")` starts its own `asyncio.run()` loop — **this works fine** because PyO3 releases the GIL during the blocking Python call, and Rust's main thread just waits. No `pyo3-async-runtimes` needed for this case (only needed if you want Rust and Python async to interleave).

---

## File structure (end state)

```
tauri-hello-world/
├── src-tauri/
│   ├── resources/
│   │   ├── python/          ← python-build-standalone (built, gitignored)
│   │   └── mcp_server/
│   │       └── server.py    ← your FastMCP tools
│   ├── src/
│   │   ├── main.rs          ← --mcp-server flag handled here
│   │   └── lib.rs           ← Tauri GUI app (PyO3 init + mcp dispatch)
│   ├── build.rs
│   └── Cargo.toml           ← pyo3 dependency
├── scripts/
│   └── setup-python.js      ← downloads + pips into bundled Python
└── package.json             ← setup-python runs in beforeBuildCommand
```

---

## Key questions before starting

1. **Target platforms?** Windows only (COM), or also Linux/macOS with COM tools disabled? → Affects whether python-build-standalone needs cross-platform handling
2. **What COM apps?** (Excel, Word, CAD tools, etc.) → Affects which pywin32 features to test
3. **Development workflow?** Do you want `npm run dev` to also spin up the MCP server for testing, or always test via Claude Desktop / MCP Inspector?
