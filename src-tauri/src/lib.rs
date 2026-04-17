use std::path::PathBuf;

// ── PyO3 ────────────────────────────────────────────────────────────────────
use pyo3::prelude::*;

// ── Compile-time resource path (dev mode) ───────────────────────────────────
// Set by build.rs; points at src-tauri/resources/ on the developer's machine.
const DEV_RESOURCES_DIR: &str = env!("CARGO_RESOURCES_DIR");

// ── Tauri command ────────────────────────────────────────────────────────────
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn call_python_hello() -> String {
    // We execute a simple Python call using our embedded environment.
    // Note: We don't use run_mcp_server here, just a standard GIL call.
    let resources = get_resource_dir();
    setup_python_env(&resources);
    
    // Ensure python is initialized (thread-safe, can be called multiple times)
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        match py.run(cr"import server; print('Ping from GUI')", None, None) {
             Ok(_) => "Python (embedded) says hello!".to_string(),
             Err(e) => format!("Python Error: {}", e)
        }
    })
}

// ── Normal Tauri GUI entry point ─────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, call_python_hello])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// ── MCP server entry point ───────────────────────────────────────────────────

/// Find the `resources/` directory at runtime.
///
/// - **Production**: resources are extracted by the installer alongside the binary.
/// - **Development**: fall back to the compile-time path inside `src-tauri/resources/`.
fn get_resource_dir() -> PathBuf {
    // 1. Try development path first if we are in a cargo environment.
    if std::env::var("CARGO_MANIFEST_DIR").is_ok() {
        let dev_path = PathBuf::from(DEV_RESOURCES_DIR);
        if dev_path.exists() {
            return dev_path;
        }
    }

    // 2. Production: resources are extracted by the installer alongside the binary.
    let exe = std::env::current_exe()
        .expect("Cannot determine executable path");
    let exe_dir = exe.parent().expect("Executable has no parent directory");

    for candidate in &[
        exe_dir.join("resources"),       // Windows NSIS / plain dir
        exe_dir.join("_up_").join("resources"), // macOS .app bundle
    ] {
        let python_path = candidate.join("python");
        // Verify it's a complete distribution by checking for lib (Unix) or Lib (Windows)
        if python_path.join("lib").exists() || python_path.join("Lib").exists() {
            return candidate.clone();
        }
    }

    // Fallback — return the best guess
    PathBuf::from(DEV_RESOURCES_DIR)
}

/// Configure `PYTHONHOME` and `PYTHONPATH` so the embedded CPython interpreter
/// finds the bundled standard library and installed packages.
fn setup_python_env(resources: &PathBuf) {
    let python_home = resources.join("python");
    let mcp_server_dir = resources.join("mcp_server");

    // PYTHONHOME tells CPython where its own stdlib lives.
    std::env::set_var("PYTHONHOME", &python_home);

    // Build PYTHONPATH: site-packages + our server code.
    #[cfg(windows)]
    let site_packages = python_home.join("Lib").join("site-packages");
    #[cfg(not(windows))]
    let site_packages = {
        let lib = python_home.join("lib");
        std::fs::read_dir(&lib)
            .ok()
            .and_then(|mut entries| {
                entries.find_map(|e| {
                    let e = e.ok()?;
                    let name = e.file_name().into_string().ok()?;
                    if name.starts_with("python3") { Some(e.path()) } else { None }
                })
            })
            .map(|p| p.join("site-packages"))
            .unwrap_or_else(|| lib.join("python3.12").join("site-packages"))
    };

    let sep = if cfg!(windows) { ";" } else { ":" };
    let pythonpath = [
        mcp_server_dir.to_string_lossy().into_owned(),
        site_packages.to_string_lossy().into_owned(),
    ]
    .join(sep);

    std::env::set_var("PYTHONPATH", pythonpath);
}

/// Run the FastMCP server on stdio.
/// Blocks until the MCP host closes the connection (EOF on stdin).
pub fn run_mcp_server() {
    let resources = get_resource_dir();
    setup_python_env(&resources);

    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        let code = cr#"
import sys
import server
server.mcp.run(transport="stdio")
"#;
        if let Err(e) = py.run(code, None, None) {
            e.print(py);
            std::process::exit(1);
        }
    });
}
