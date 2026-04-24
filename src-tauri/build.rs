fn main() {
    tauri_build::build();

    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let resources_dir = format!("{}/resources", manifest_dir);

    // Expose the resources directory path as a compile-time constant
    // so that Rust code can find mcp_server/ in dev mode.
    println!("cargo:rustc-env=CARGO_RESOURCES_DIR={}", resources_dir);

    // Re-run if the mcp_server directory changes
    println!("cargo:rerun-if-changed=resources/mcp_server");
}
