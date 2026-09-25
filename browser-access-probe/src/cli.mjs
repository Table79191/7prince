#!/usr/bin/env node
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { classifyResponse, validateTarget } from './detect.mjs';

function parseArgs(argv) {
  const args = {
    headed: false,
    outDir: 'artifacts',
    profileDir: undefined,
    storageState: undefined,
    timeoutMs: 30000,
    waitMs: 1500
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--headed') args.headed = true;
    else if (a === '--out' && argv[i + 1]) args.outDir = argv[++i];
    else if (a === '--profile-dir' && argv[i + 1]) args.profileDir = argv[++i];
    else if (a === '--storage-state' && argv[i + 1]) args.storageState = argv[++i];
    else if (a === '--timeout' && argv[i + 1]) args.timeoutMs = Number(argv[++i]);
    else if (a === '--wait' && argv[i + 1]) args.waitMs = Number(argv[++i]);
    else if (!args.url) args.url = a;
    else throw new Error(`Unknown argument: ${a}`);
  }

  if (!args.url) {
    throw new Error('Usage: npm run probe -- <url> [--headed] [--profile-dir dir] [--storage-state state.json] [--out artifacts]');
  }
  if (args.profileDir && args.storageState) {
    throw new Error('Use either --profile-dir or --storage-state, not both.');
  }
  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs < 1000 || args.timeoutMs > 120000) {
    throw new Error('--timeout must be between 1000 and 120000 ms.');
  }
  if (!Number.isFinite(args.waitMs) || args.waitMs < 0 || args.waitMs > 10000) {
    throw new Error('--wait must be between 0 and 10000 ms.');
  }
  return args;
}

function safeStamp() {
  return new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const target = validateTarget(args.url);
  const outDir = path.resolve(args.outDir);
  await mkdir(outDir, { recursive: true });

  let browser;
  let context;

  if (args.profileDir) {
    const profileDir = path.resolve(args.profileDir);
    await mkdir(profileDir, { recursive: true });
    context = await chromium.launchPersistentContext(profileDir, {
      headless: !args.headed,
      locale: 'ko-KR'
    });
  } else {
    browser = await chromium.launch({ headless: !args.headed });
    context = await browser.newContext({
      storageState: args.storageState,
      locale: 'ko-KR'
    });
  }

  const pages = context.pages();
  const page = pages[0] ?? await context.newPage();

  const events = [];
  page.on('console', (msg) => events.push({ type: 'console', level: msg.type(), text: msg.text() }));
  page.on('pageerror', (err) => events.push({ type: 'pageerror', text: err.message }));
  page.on('requestfailed', (req) => events.push({ type: 'requestfailed', url: req.url(), error: req.failure()?.errorText }));

  const started = Date.now();
  let response;
  let navigationError = null;

  try {
    response = await page.goto(target.href, {
      waitUntil: 'domcontentloaded',
      timeout: args.timeoutMs
    });
    if (args.waitMs) await page.waitForTimeout(args.waitMs);
  } catch (err) {
    navigationError = err instanceof Error ? err.message : String(err);
  }

  const status = response?.status() ?? 0;
  const finalUrl = page.url();
  const title = await page.title().catch(() => '');
  const bodyText = await page.locator('body').innerText({ timeout: 3000 }).catch(() => '');
  const html = await page.content().catch(() => '');
  const verdict = classifyResponse({ status, title, bodyText });
  if (navigationError && status === 0) verdict.classification = 'navigation-failed';

  const stamp = safeStamp();
  const shotPath = path.join(outDir, `probe-${stamp}.png`);
  const htmlPath = path.join(outDir, `probe-${stamp}.html`);
  const reportPath = path.join(outDir, `probe-${stamp}.json`);

  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});
  await writeFile(htmlPath, html, 'utf8');

  const usingPersistentProfile = Boolean(args.profileDir);
  const report = {
    requestedUrl: target.href,
    finalUrl,
    status,
    title,
    classification: verdict.classification,
    signals: verdict.signals,
    navigationError,
    elapsedMs: Date.now() - started,
    session: {
      mode: usingPersistentProfile ? 'persistent-profile' : args.storageState ? 'storage-state' : 'temporary',
      profileDir: usingPersistentProfile ? path.resolve(args.profileDir) : null
    },
    artifacts: { screenshot: shotPath, html: htmlPath },
    notes: [
      usingPersistentProfile
        ? 'Cookies and local browser state are retained in the selected profile directory for later runs.'
        : 'Use --profile-dir to retain cookies and local browser state between runs.',
      'This tool does not solve CAPTCHAs, spoof browser fingerprints, rotate proxies, or bypass access controls.'
    ],
    events: events.slice(-50)
  };

  await writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify({ ...report, artifacts: { ...report.artifacts, report: reportPath } }, null, 2));

  if (args.headed && ['access-blocked', 'challenge-detected'].includes(report.classification)) {
    console.error('\nAccess verification is still required in the visible browser. Complete it normally, then close the browser; this profile will be reused next time.');
    await page.waitForEvent('close', { timeout: 0 }).catch(() => {});
  }

  await context.close().catch(() => {});
  if (browser) await browser.close().catch(() => {});

  process.exitCode = ['reachable', 'client-error', 'server-error'].includes(report.classification) ? 0 : 2;
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack : String(err));
  process.exitCode = 1;
});
