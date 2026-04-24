use std::path::{Path, PathBuf};
use std::process::Command;

// ── Compile-time resource path (dev mode) ───────────────────────────────────
// Set by build.rs; points at src-tauri/resources/ on the developer's machine.
const DEV_RESOURCES_DIR: &str = env!("CARGO_RESOURCES_DIR");

// ── Tauri commands ───────────────────────────────────────────────────────────

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

/// Health-check command: finds Python, ensures venv, returns version string.
/// Used by the GUI to confirm Python is available.
#[tauri::command]
fn call_python_hello() -> String {
    let resources = get_resource_dir();
    let requirements = resources.join("mcp_server").join("requirements.txt");

    let system_python = match find_system_python() {
        Some(p) => p,
        None => return "❌ Python 3.10+ not found. Please install Python from python.org and ensure it is on PATH.".to_string(),
    };

    match ensure_venv(&system_python, &requirements) {
        Ok(venv_py) => {
            match Command::new(&venv_py)
                .args(["-c", "import sys; print(f'Python {sys.version} is ready!')"])
                .output()
            {
                Ok(out) if out.status.success() => {
                    String::from_utf8_lossy(&out.stdout).trim().to_string()
                }
                Ok(out) => String::from_utf8_lossy(&out.stderr).trim().to_string(),
                Err(e) => format!("Failed to run Python: {e}"),
            }
        }
        Err(e) => format!("Failed to set up Python environment: {e}"),
    }
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

/// Run the FastMCP server on stdio.
///
/// Finds the user's Python, ensures a venv with dependencies, then
/// **replaces the process** (exec on Unix) or **spawns-and-waits** (Windows)
/// so that the MCP host talks directly to Python via stdio.
pub fn run_mcp_server() {
    let resources = get_resource_dir();
    let requirements = resources.join("mcp_server").join("requirements.txt");
    let server_py = resources.join("mcp_server").join("server.py");
    let mcp_server_dir = resources.join("mcp_server");

    let system_python = find_system_python().unwrap_or_else(|| {
        eprintln!("[mcp] ERROR: Python 3.10+ not found. Please install Python from python.org");
        std::process::exit(1);
    });

    let venv_py = ensure_venv(&system_python, &requirements).unwrap_or_else(|e| {
        eprintln!("[mcp] ERROR: Failed to set up Python environment: {e}");
        std::process::exit(1);
    });

    eprintln!("[mcp] Launching server: {} {}", venv_py.display(), server_py.display());

    // On Unix: exec() replaces this process — Claude Desktop talks directly to Python.
    // On Windows: spawn + forward exit code (no true exec syscall).
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let err = Command::new(&venv_py)
            .arg(&server_py)
            .env("PYTHONPATH", &mcp_server_dir)
            .current_dir(&mcp_server_dir)
            .exec(); // never returns on success
        eprintln!("[mcp] ERROR: exec failed: {err}");
        std::process::exit(1);
    }

    #[cfg(not(unix))]
    {
        let status = Command::new(&venv_py)
            .arg(&server_py)
            .env("PYTHONPATH", &mcp_server_dir)
            .current_dir(&mcp_server_dir)
            .status()
            .unwrap_or_else(|e| {
                eprintln!("[mcp] ERROR: Failed to launch Python: {e}");
                std::process::exit(1);
            });
        std::process::exit(status.code().unwrap_or(1));
    }
}

// ── Setup CLI entry point ────────────────────────────────────────────────────

/// Command line entry point for pre-creating the Python environment.
/// Called by dev tools like `setup-python.js` to ensure the venv exists.
pub fn setup_python_cli() {
    let resources = get_resource_dir();
    let requirements = resources.join("mcp_server").join("requirements.txt");

    println!("\n🔍  Finding system Python...");
    let system_python = find_system_python().unwrap_or_else(|| {
        eprintln!("❌  Python 3.10+ not found on PATH or in common install locations.");
        eprintln!("    Install Python from https://python.org and ensure it is on PATH.\n");
        std::process::exit(1);
    });
    println!("✓  Python -> {}\n", system_python.display());

    match ensure_venv(&system_python, &requirements) {
        Ok(venv_py) => {
            println!("✓  Venv created/verified -> {}", venv_py.display());
            println!("✅  Setup complete!\n");
        }
        Err(e) => {
            eprintln!("❌  Failed to set up Python environment: {e}");
            std::process::exit(1);
        }
    }
}

// ── Python discovery ─────────────────────────────────────────────────────────

/// Try to run a Python executable and return its path if it is version ≥ 3.10.
fn probe_python(cmd: &str, extra_args: &[&str]) -> Option<PathBuf> {
    let output = Command::new(cmd)
        .args(extra_args)
        .args(["-c", "import sys; v=sys.version_info; print(v.major, v.minor, sys.executable)"])
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let s = String::from_utf8_lossy(&output.stdout);
    let parts: Vec<&str> = s.trim().splitn(3, ' ').collect();
    if parts.len() < 3 {
        return None;
    }

    let major: u32 = parts[0].parse().ok()?;
    let minor: u32 = parts[1].parse().ok()?;
    if major < 3 || (major == 3 && minor < 10) {
        return None;
    }

    let exe = PathBuf::from(parts[2]);
    if exe.exists() { Some(exe) } else { None }
}

/// Search for a user-installed Python ≥ 3.10.
fn find_system_python() -> Option<PathBuf> {
    // Common command names on PATH
    for cmd in &["python3", "python"] {
        if let Some(p) = probe_python(cmd, &[]) {
            return Some(p);
        }
    }

    // Windows Python Launcher
    #[cfg(windows)]
    if let Some(p) = probe_python("py", &["-3"]) {
        return Some(p);
    }

    // Windows: common user-install locations under %LOCALAPPDATA%\Programs\Python
    #[cfg(windows)]
    {
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            let programs = PathBuf::from(local).join("Programs").join("Python");
            if let Ok(entries) = std::fs::read_dir(&programs) {
                let mut dirs: Vec<_> = entries
                    .filter_map(|e| e.ok())
                    .filter(|e| e.file_name().to_string_lossy().starts_with("Python3"))
                    .collect();
                // Sort descending so newest version wins
                dirs.sort_by(|a, b| b.file_name().cmp(&a.file_name()));
                for entry in dirs {
                    let exe = entry.path().join("python.exe");
                    if let Some(p) = probe_python(exe.to_str().unwrap_or(""), &[]) {
                        return Some(p);
                    }
                }
            }
        }
    }

    None
}

// ── Venv management ──────────────────────────────────────────────────────────

/// Base directory for app data (venv lives here).
fn app_data_dir() -> PathBuf {
    #[cfg(windows)]
    {
        std::env::var("LOCALAPPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("."))
            .join("EngineeringTools")
            .join("tauri-hello-world")
    }
    #[cfg(not(windows))]
    {
        std::env::var("XDG_DATA_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                PathBuf::from(std::env::var("HOME").unwrap_or_default())
                    .join(".local")
                    .join("share")
            })
            .join("EngineeringTools")
            .join("tauri-hello-world")
    }
}

fn venv_dir() -> PathBuf {
    app_data_dir().join("venv")
}

fn venv_python(venv: &Path) -> PathBuf {
    #[cfg(windows)]
    return venv.join("Scripts").join("python.exe");
    #[cfg(not(windows))]
    return venv.join("bin").join("python");
}

/// Simple content hash used to detect when requirements.txt has changed.
fn file_hash(path: &Path) -> u64 {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let content = std::fs::read(path).unwrap_or_default();
    let mut h = DefaultHasher::new();
    content.hash(&mut h);
    h.finish()
}

/// Idempotently create the venv and install requirements.
/// Returns the path to the venv Python executable.
fn ensure_venv(system_python: &Path, requirements: &Path) -> Result<PathBuf, String> {
    let venv = venv_dir();
    let python = venv_python(&venv);

    // Create venv if missing
    if !python.exists() {
        eprintln!("[mcp] Creating venv at {} ...", venv.display());
        std::fs::create_dir_all(&venv).map_err(|e| e.to_string())?;
        let status = Command::new(system_python)
            .args(["-m", "venv"])
            .arg(&venv)
            .status()
            .map_err(|e| e.to_string())?;
        if !status.success() {
            return Err(format!("Failed to create venv at {}", venv.display()));
        }
    }

    // Install/update requirements when the file has changed (stamp file tracks hash)
    let stamp = venv.join(".requirements_stamp");
    let current_hash = format!("{:016x}", file_hash(requirements));
    let needs_install = std::fs::read_to_string(&stamp)
        .map(|s| s.trim() != current_hash)
        .unwrap_or(true);

    if needs_install && requirements.exists() {
        eprintln!("[mcp] Installing Python requirements ...");
        
        // Remove the stamp before installing, so if pip fails midway or is interrupted, 
        // the stamp is not left in a valid state while the venv is broken.
        let _ = std::fs::remove_file(&stamp);
        
        let status = Command::new(&python)
            .args(["-m", "pip", "install", "-q", "--disable-pip-version-check", "-r"])
            .arg(requirements)
            .status()
            .map_err(|e| e.to_string())?;
        if status.success() {
            let _ = std::fs::write(&stamp, &current_hash);
        } else {
            return Err("pip install failed".to_string());
        }
    }

    Ok(python)
}

// ── Resource directory (dev vs production) ───────────────────────────────────

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
