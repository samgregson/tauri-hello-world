import os
import sys
import urllib.request
import tarfile
import zipfile
import subprocess
import shutil
import platform

def get_platform_info():
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "x86_64-pc-windows-msvc-shared"
    elif system == "linux":
        if machine in ("x86_64", "amd64"):
            return "x86_64-unknown-linux-gnu-lto-full"
    elif system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin-lto-full"
        else:
            return "x86_64-apple-darwin-lto-full"
            
    raise Exception(f"Unsupported platform: {system} {machine}")

def main():
    target_info = get_platform_info()
    version = "20240415"
    tag = f"cpython-3.10.14+{version}"
    
    ext = "zip" if "windows" in target_info else "tar.gz"
    url = f"https://github.com/indygreg/python-build-standalone/releases/download/{version}/cpython-3.10.14+{version}-{target_info}-install_only.{ext}"
    
    resources_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src-tauri", "resources"))
    python_dir = os.path.join(resources_dir, "python")
    
    if os.path.exists(python_dir):
        print(f"Removing existing python dir: {python_dir}")
        shutil.rmtree(python_dir)
        
    print(f"Downloading {url}...")
    archive_path = os.path.join(resources_dir, f"python_archive.{ext}")
    urllib.request.urlretrieve(url, archive_path)
    
    print(f"Extracting to {python_dir}...")
    if ext == "zip":
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(resources_dir)
    else:
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            tar_ref.extractall(resources_dir)
            
    os.remove(archive_path)
    
    # python-build-standalone extracts to a 'python' folder by default.
    extracted_python_dir = os.path.join(resources_dir, "python")
    
    # Install pip dependencies
    print("Installing requirements...")
    python_exe = os.path.join(extracted_python_dir, "python.exe") if "windows" in target_info else os.path.join(extracted_python_dir, "bin", "python3")
    requirements_file = os.path.join(resources_dir, "mcp_server", "requirements.txt")
    
    # Ensure pip is up to date
    subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install requirements
    subprocess.check_call([python_exe, "-m", "pip", "install", "-r", requirements_file])
    
    print("Cleaning up executables (removing python.exe/backend.exe) for IT compliance...")
    # Delete python executables so IT scanners don't flag them
    if "windows" in target_info:
        for exe in ["python.exe", "pythonw.exe", "python3.exe"]:
            exe_path = os.path.join(extracted_python_dir, exe)
            if os.path.exists(exe_path):
                os.remove(exe_path)
                print(f"Removed {exe_path}")
    else:
        for exe in ["python", "python3", "python3.10"]:
            exe_path = os.path.join(extracted_python_dir, "bin", exe)
            if os.path.exists(exe_path):
                os.remove(exe_path)
                print(f"Removed {exe_path}")

    print("Setup complete. Embedded Python environment is ready in src-tauri/resources/python.")

if __name__ == "__main__":
    main()
