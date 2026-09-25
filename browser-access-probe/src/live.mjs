#!/usr/bin/env node
import { spawn } from 'node:child_process';
import process from 'node:process';

const endpoint = 'http://127.0.0.1:9222';

async function cdpReady() {
  try {
    const res = await fetch(`${endpoint}/json/version`, { signal: AbortSignal.timeout(1000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForCdp(maxMs = 15000) {
  const started = Date.now();
  while (Date.now() - started < maxMs) {
    if (await cdpReady()) return true;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function runNode(args) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, { stdio: 'inherit' });
    child.on('error', reject);
    child.on('exit', (code, signal) => {
      if (signal) reject(new Error(`Child process terminated by signal ${signal}`));
      else resolve(code ?? 1);
    });
  });
}

async function main() {
  const target = process.argv[2];
  if (!target) {
    throw new Error('Usage: npm run live -- <url>');
  }

  if (!(await cdpReady())) {
    const launchCode = await runNode(['src/start-local-chrome.mjs']);
    if (launchCode !== 0) {
      throw new Error(`Chrome launcher exited with code ${launchCode}`);
    }
  }

  if (!(await waitForCdp())) {
    throw new Error(`Local Chrome did not expose ${endpoint}. Keep Chrome allowed through local firewall and retry.`);
  }

  console.log(`Attaching to local Chrome at ${endpoint}`);
  const code = await runNode([
    'src/cli.mjs',
    target,
    '--cdp',
    endpoint,
    '--interactive-wait',
    '180000',
    '--wait',
    '2500'
  ]);

  process.exitCode = code;
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack : String(err));
  process.exitCode = 1;
});
