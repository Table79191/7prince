#!/usr/bin/env node
import { access, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';

async function exists(file) {
  try {
    await access(file);
    return true;
  } catch {
    return false;
  }
}

async function findChrome() {
  const candidates = [];

  if (process.platform === 'win32') {
    const local = process.env.LOCALAPPDATA;
    const pf = process.env.PROGRAMFILES;
    const pf86 = process.env['PROGRAMFILES(X86)'];

    if (local) candidates.push(path.join(local, 'Google', 'Chrome', 'Application', 'chrome.exe'));
    if (pf) candidates.push(path.join(pf, 'Google', 'Chrome', 'Application', 'chrome.exe'));
    if (pf86) candidates.push(path.join(pf86, 'Google', 'Chrome', 'Application', 'chrome.exe'));
  } else if (process.platform === 'darwin') {
    candidates.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  } else {
    candidates.push('/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser');
  }

  for (const candidate of candidates) {
    if (await exists(candidate)) return candidate;
  }

  throw new Error('Google Chrome/Chromium was not found in a standard installation path.');
}

async function main() {
  const port = Number(process.env.BROWSER_PROBE_CDP_PORT || 9222);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error('BROWSER_PROBE_CDP_PORT must be an integer between 1024 and 65535.');
  }

  const chrome = await findChrome();
  const profileDir = path.resolve(process.env.BROWSER_PROBE_CHROME_PROFILE || '.live-chrome-profile');
  await mkdir(profileDir, { recursive: true });

  const child = spawn(chrome, [
    `--remote-debugging-port=${port}`,
    '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${profileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank'
  ], {
    detached: true,
    stdio: 'ignore'
  });

  child.unref();

  console.log(`Chrome started with persistent profile: ${profileDir}`);
  console.log(`CDP endpoint: http://127.0.0.1:${port}`);
  console.log('Keep this Chrome window open. Use npm run attach -- <url> to navigate with this exact session.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack : String(err));
  process.exitCode = 1;
});
