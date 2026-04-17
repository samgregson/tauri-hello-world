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
        // Delay-load the Python DLL. This serves two vital purposes:
        // 1. Prevents immediate crash if python312.dll is not precisely next to the EXE.
        // 2. Reduces AV heuristic flags, as the executable doesn't statically bind the scripting engine.
        println!("cargo:rustc-link-arg=delayimp.lib");
        println!("cargo:rustc-link-arg=/DELAYLOAD:python312.dll");
    }

    // Re-run if the python directory appears or changes
    println!("cargo:rerun-if-changed=resources/python");
    println!("cargo:rerun-if-env-changed=PYO3_PYTHON");
}
