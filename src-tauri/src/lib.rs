use std::path::PathBuf;
use pyo3::prelude::*;

// ── Compile-time resource path (dev mode) ───────────────────────────────────
// Set by build.rs; points at src-tauri/resources/ on the developer's machine.
const DEV_RESOURCES_DIR: &str = env!("CARGO_RESOURCES_DIR");

fn get_resource_dir() -> PathBuf {
    // Dev mode: use compile-time path
    if std::env::var("CARGO_MANIFEST_DIR").is_ok() {
        let dev_path = PathBuf::from(DEV_RESOURCES_DIR);
        if dev_path.exists() {
            return dev_path;
        }
    }

    // Production: resources extracted by installer alongside the binary
    let exe = std::env::current_exe().expect("Cannot determine executable path");
    let exe_dir = exe.parent().expect("Executable has no parent directory");

    for candidate in &[
        exe_dir.join("resources"),
        exe_dir.join("_up_").join("resources"), // macOS .app bundle
    ] {
        if candidate.join("mcp_server").exists() {
            return candidate.clone();
        }
    }

    PathBuf::from(DEV_RESOURCES_DIR)
}

/// Initialize the embedded Python environment.
fn init_python() {
    let resources = get_resource_dir();
    let python_dir = resources.join("python");
    
    // Set PYTHONHOME to point to our headless python distribution
    std::env::set_var("PYTHONHOME", &python_dir);
    
    // Add the python dir to PATH so dynamic libraries can be found
    if let Ok(path) = std::env::var("PATH") {
        #[cfg(windows)]
        let new_path = format!("{};{}", python_dir.display(), path);
        #[cfg(unix)]
        let new_path = format!("{}:{}", python_dir.display(), path);
        
        std::env::set_var("PATH", new_path);
    }
    
    // Set PYTHONPATH to include our mcp_server and the site-packages
    let mcp_server = resources.join("mcp_server");
    
    #[cfg(windows)]
    let site_packages = python_dir.join("Lib").join("site-packages");
    #[cfg(unix)]
    let site_packages = python_dir.join("lib").join("python3.10").join("site-packages");
    
    #[cfg(windows)]
    let pythonpath = format!("{};{}", mcp_server.display(), site_packages.display());
    #[cfg(unix)]
    let pythonpath = format!("{}:{}", mcp_server.display(), site_packages.display());
    
    std::env::set_var("PYTHONPATH", pythonpath);
    
    // Initialize PyO3
    pyo3::prepare_freethreaded_python();
}

// ── Tauri commands ───────────────────────────────────────────────────────────

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

/// Health-check command: confirms embedded Python is working via PyO3.
#[tauri::command]
fn call_python_hello() -> String {
    Python::with_gil(|py| {
        let sys = py.import("sys").map_err(|e| e.to_string())?;
        let version: String = sys.getattr("version").map_err(|e| e.to_string())?.extract().map_err(|e| e.to_string())?;
        Ok::<String, String>(format!("Python {} is ready! (Embedded PyO3)", version))
    }).unwrap_or_else(|e| format!("Failed to run Python: {}", e))
}

#[tauri::command]
fn get_mcp_tools() -> Result<String, String> {
    Python::with_gil(|py| {
        let test_mcp = py.import("test_mcp").map_err(|e| e.to_string())?;
        let result: String = test_mcp.call_method0("get_tools_json")
            .map_err(|e| e.to_string())?
            .extract()
            .map_err(|e| e.to_string())?;
        Ok(result)
    })
}

#[tauri::command]
fn test_mcp_tool(tool_name: String, args_json: String) -> Result<String, String> {
    Python::with_gil(|py| {
        let test_mcp = py.import("test_mcp").map_err(|e| e.to_string())?;
        let result: String = test_mcp.call_method1("test_tool_json", (tool_name, args_json))
            .map_err(|e| e.to_string())?
            .extract()
            .map_err(|e| e.to_string())?;
        Ok(result)
    })
}

// ── Normal Tauri GUI entry point ─────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    init_python();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet, 
            call_python_hello, 
            get_mcp_tools, 
            test_mcp_tool
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// ── MCP server entry point ───────────────────────────────────────────────────

/// Run the FastMCP server directly via PyO3.
pub fn run_mcp_server() {
    init_python();

    let res = Python::with_gil(|py| {
        let server_mod = py.import("server").map_err(|e| e.to_string())?;
        let mcp = server_mod.getattr("mcp").map_err(|e| e.to_string())?;
        
        // Pass "stdio" transport via keyword arg or directly if supported
        let kwargs = pyo3::types::PyDict::new(py);
        kwargs.set_item("transport", "stdio").map_err(|e| e.to_string())?;
        
        mcp.call_method("run", (), Some(&kwargs)).map_err(|e| e.to_string())?;
        Ok::<(), String>(())
    });

    if let Err(e) = res {
        eprintln!("[mcp] ERROR: MCP Server failed: {}", e);
        std::process::exit(1);
    }
}

// ── Setup CLI entry point ────────────────────────────────────────────────────

/// Setup Python CLI is now a no-op since Python is embedded, but we keep the signature.
pub fn setup_python_cli() {
    init_python();
    println!("✓ Embedded Python setup verified via PyO3.");
}
