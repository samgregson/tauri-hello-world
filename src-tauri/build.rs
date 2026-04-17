fn main() {
    tauri_build::build();

    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let resources_dir = format!("{}/resources", manifest_dir);

    // Expose the resources directory path as a compile-time constant
    // so that Rust code can find Python in dev mode (before Tauri installs resources).
    println!("cargo:rustc-env=CARGO_RESOURCES_DIR={}", resources_dir);

    // ── Link + RPATH for bundled libpython (Linux / macOS dev) ───────────────
    // On Windows, PyO3 links against python3xx.dll which is in %PATH% or alongside the exe.
    // On Linux, we need to tell the linker where libpython.so lives and bake an RPATH
    // so the binary can find it at runtime without LD_LIBRARY_PATH.
    #[cfg(unix)]
    {
        let lib_dir = format!("{}/python/lib", resources_dir);
        let lib_path = std::path::Path::new(&lib_dir);
        if lib_path.exists() {
            println!("cargo:rustc-link-search=native={}", lib_dir);
            // Bake an absolute RPATH for development builds.
            println!("cargo:rustc-link-arg=-Wl,-rpath,{}", lib_dir);
        }
    }

    #[cfg(windows)]
    {
        // MSVC does not support delay-loading DLLs that export data symbols, so 
        // /DELAYLOAD:python312.dll fails to link.
        // Instead, we copy the required Python DLLs directly into the target output 
        // directory (next to the executable) so the Windows PE loader finds them immediately.
        
        if let Ok(out_dir) = std::env::var("OUT_DIR") {
            let target_dir = std::path::PathBuf::from(out_dir).join("../../../");
            
            let py312_src = std::path::Path::new(&resources_dir).join("python/python312.dll");
            let py312_dest = target_dir.join("python312.dll");
            if py312_src.exists() {
                let _ = std::fs::copy(&py312_src, &py312_dest);
            }
            
            let py3_src = std::path::Path::new(&resources_dir).join("python/python3.dll");
            let py3_dest = target_dir.join("python3.dll");
            if py3_src.exists() {
                let _ = std::fs::copy(&py3_src, &py3_dest);
            }
        }
    }

    // Re-run if the python directory appears or changes
    println!("cargo:rerun-if-changed=resources/python");
    println!("cargo:rerun-if-env-changed=PYO3_PYTHON");
}
