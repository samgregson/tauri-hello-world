#!/usr/bin/env node
/**
 * setup-python.js
 *
 * Development helper: finds the user's system Python, creates the app venv,
 * and installs required packages into it.
 *
 * This is OPTIONAL — the Tauri app does the same automatically at runtime.
 * Run it manually to pre-warm the environment or verify Python is on PATH.
 *
 * Run: node scripts/setup-python.js
 */

import { execSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const requirementsTxt = join(projectRoot, 'src-tauri', 'resources', 'mcp_server', 'requirements.txt');

// ── Venv location — must match the paths used in src-tauri/src/lib.rs ────────
function getVenvDir() {
  if (os.platform() === 'win32') {
    const base = process.env.LOCALAPPDATA || join(os.homedir(), 'AppData', 'Local');
    return join(base, 'EngineeringTools', 'venv');
  }
  const base = process.env.XDG_DATA_HOME || join(os.homedir(), '.local', 'share');
  return join(base, 'EngineeringTools', 'venv');
}

function getVenvPython(venvDir) {
  return os.platform() === 'win32'
    ? join(venvDir, 'Scripts', 'python.exe')
    : join(venvDir, 'bin', 'python');
}

// ── Python discovery ─────────────────────────────────────────────────────────
function probePython(cmd, extraArgs = []) {
  const result = spawnSync(
    cmd,
    [...extraArgs, '-c', 'import sys; v=sys.version_info; print(v.major, v.minor, sys.executable)'],
    { encoding: 'utf8', timeout: 5000, windowsHide: true }
  );
  if (result.status !== 0 || !result.stdout) return null;

  const parts = result.stdout.trim().split(' ');
  if (parts.length < 3) return null;

  const major = parseInt(parts[0], 10);
  const minor = parseInt(parts[1], 10);
  const exe = parts.slice(2).join(' ');

  if (major < 3 || (major === 3 && minor < 10)) {
    console.warn(`  ⚠  Found Python ${major}.${minor} at "${exe}" — requires 3.10+, skipping`);
    return null;
  }

  return { version: `${major}.${minor}`, exe };
}

function findSystemPython() {
  const candidates = [
    () => probePython('python3'),
    () => probePython('python'),
  ];

  if (os.platform() === 'win32') {
    candidates.push(() => probePython('py', ['-3']));

    // Common Windows user-install locations
    const localAppData = process.env.LOCALAPPDATA || '';
    for (const ver of ['Python313', 'Python312', 'Python311', 'Python310']) {
      const exe = join(localAppData, 'Programs', 'Python', ver, 'python.exe');
      if (existsSync(exe)) candidates.push(() => probePython(exe));
    }
  }

  for (const probe of candidates) {
    const result = probe();
    if (result) return result;
  }
  return null;
}

// ── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  console.log('\n🔍  Finding system Python...\n');

  const python = findSystemPython();
  if (!python) {
    console.error('❌  Python 3.10+ not found on PATH or in common install locations.');
    console.error('    Install Python from https://python.org and ensure it is on PATH.\n');
    process.exit(1);
  }
  console.log(`✓  Python ${python.version}  →  ${python.exe}\n`);

  const venvDir = getVenvDir();
  const venvPython = getVenvPython(venvDir);

  // Create venv if it does not already exist
  if (existsSync(venvPython)) {
    console.log(`✓  Venv already exists:\n   ${venvDir}\n`);
  } else {
    console.log(`Creating venv at:\n   ${venvDir}\n`);
    mkdirSync(venvDir, { recursive: true });
    execSync(`"${python.exe}" -m venv "${venvDir}"`, { stdio: 'inherit' });
    console.log('\n✓  Venv created\n');
  }

  // Install requirements
  console.log('Installing Python requirements...');
  execSync(
    `"${venvPython}" -m pip install -q --disable-pip-version-check -r "${requirementsTxt}"`,
    { stdio: 'inherit' }
  );
  console.log('✓  Requirements installed\n');

  // Clean up legacy PYO3_PYTHON from .cargo/config.toml (safe no-op if already clean)
  const cargoConfig = join(projectRoot, '.cargo', 'config.toml');
  mkdirSync(join(projectRoot, '.cargo'), { recursive: true });
  writeFileSync(cargoConfig, '# Cargo configuration — Python is user-installed, not embedded\n');
  console.log('✓  .cargo/config.toml cleaned\n');

  console.log('✅  setup-python complete!\n');
  console.log('Next steps:');
  console.log('  npm run tauri dev    — start the app in dev mode');
  console.log('  npm run tauri build  — build the release installer\n');
}

main().catch(err => {
  console.error('\n❌  setup-python failed:', err.message);
  process.exit(1);
});
