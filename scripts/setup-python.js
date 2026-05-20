#!/usr/bin/env node
/**
 * setup-python.js
 *
 * Development helper: delegates to the Rust binary to find the user's system Python, 
 * create the app venv, and install required packages into it.
 *
 * Run: node scripts/setup-python.js
 */

import { execSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

async function main() {
  console.log('\n🔍  Delegating to Rust setup handler...\n');

  // Clean up legacy PYO3_PYTHON from .cargo/config.toml (safe no-op if already clean)
  const cargoConfig = join(projectRoot, '.cargo', 'config.toml');
  mkdirSync(join(projectRoot, '.cargo'), { recursive: true });
  writeFileSync(cargoConfig, '# Cargo configuration — Python is user-installed, not embedded\n');
  console.log('✓  .cargo/config.toml cleaned\n');

  try {
    // Run the setup logic implemented inside the Tauri app's binary
    execSync('cargo run -- --setup-python', {
      cwd: join(projectRoot, 'src-tauri'),
      stdio: 'inherit'
    });
  } catch (err) {
    console.error('\n❌  setup-python failed');
    process.exit(1);
  }

  console.log('Next steps:');
  console.log('  npm run tauri dev    — start the app in dev mode');
  console.log('  npm run tauri build  — build the release installer\n');
}

main().catch(err => {
  console.error('\n❌  setup-python failed:', err.message);
  process.exit(1);
});
