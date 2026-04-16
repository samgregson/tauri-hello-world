const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * This script builds the Python backend using PyInstaller and moves it to the 
 * correct location for Tauri to find it as a sidecar.
 * 
 * Usage: node scripts/build-backend.js [target-triple]
 */

let targetTriple = process.env.TARGET_TRIPLE || process.argv[2];

if (!targetTriple) {
  // Simple auto-detection for local dev
  const arch = process.arch === 'x64' ? 'x86_64' : (process.arch === 'arm64' ? 'aarch64' : process.arch);
  if (process.platform === 'linux') {
    targetTriple = `${arch}-unknown-linux-gnu`;
  } else if (process.platform === 'win32') {
    targetTriple = `${arch}-pc-windows-msvc`;
  } else if (process.platform === 'darwin') {
    targetTriple = `${arch}-apple-darwin`;
  }
}

if (!targetTriple) {
  console.error('Error: Please provide a target triple (e.g., x86_64-unknown-linux-gnu)');
  console.log('Usage: node scripts/build-backend.js <target-triple>');
  process.exit(1);
}

const isWindows = process.platform === 'win32' || targetTriple.includes('windows');
const ext = isWindows ? '.exe' : '';

// Function to find PyInstaller
function getPyInstaller() {
  // 1. Check if it's in the PATH (preferred for CI)
  try {
    execSync('pyinstaller --version', { stdio: 'ignore' });
    return 'pyinstaller';
  } catch (e) {}

  // 2. Check for venv (common for local dev)
  const venvPath = isWindows 
    ? path.join('.venv', 'Scripts', 'pyinstaller.exe')
    : path.join('venv', 'bin', 'pyinstaller');
  
  if (fs.existsSync(venvPath)) {
    return venvPath;
  }

  // 3. Fallback to python -m PyInstaller
  return 'python -m PyInstaller';
}

const pyInstaller = getPyInstaller();

console.log(`--- Building Backend Sidecar ---`);
console.log(`Target Triple: ${targetTriple}`);
console.log(`Using: ${pyInstaller}`);

try {
  // Run PyInstaller
  // --onefile: Bundle into a single executable
  // --noconsole: Don't show a terminal window when running (important for GUI apps)
  execSync(`${pyInstaller} --onefile --noconsole backend/main.py --name backend`, { stdio: 'inherit' });

  const src = path.join('dist', `backend${ext}`);
  const destDir = path.join('src-tauri', 'bin');
  const destName = `backend-${targetTriple}${ext}`;
  const dest = path.join(destDir, destName);

  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  // Copy/Move to the sidecar location
  if (fs.existsSync(dest)) {
    fs.unlinkSync(dest);
  }

  fs.copyFileSync(src, dest);
  console.log(`\n✅ Success! Sidecar built: ${dest}`);
} catch (error) {
  console.error('\n❌ Failed to build backend sidecar.');
  console.error(error.message);
  process.exit(1);
}
