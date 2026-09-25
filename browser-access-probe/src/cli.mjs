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
    storageState: undefined,
    timeoutMs: 30000,
    waitMs: 1500
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--headed') args.headed = true;
    else if (a === '--out' && argv[i + 1]) args.outDir = argv[++i];
    else if (a === '--storage-state' && argv[i + 1]) args.storageState = argv[++i];
    else if (a === '--timeout' && argv[i + 1]) args.timeoutMs = Number(argv[++i]);
    else if (a === '--wait' && argv[i + 1]) args.waitMs = Number(argv[++i]);
    else if (!args.url) args.url = a;
    else throw new Error(`Unknown argument: ${a}`);
  }

  if (!args.url) {
    throw new Error('Usage: npm run probe -- <url> [--headed] [--storage-state state.json] [--out artifacts]');
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

  const browser = await chromium.launch({ headless: !args.headed });
  const context = await browser.newContext({
    storageState: args.storageState,
    locale: 'ko-KR'
  });
  const page = await context.newPage();

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

  const report = {
    requestedUrl: target.href,
    finalUrl,
    status,
    title,
    classification: verdict.classification,
    signals: verdict.signals,
    navigationError,
    elapsedMs: Date.now() - started,
    artifacts: { screenshot: shotPath, html: htmlPath },
    notes: [
      'This tool does not solve CAPTCHAs, rotate proxies, spoof browser fingerprints, or bypass access controls.',
      'If a site requires login, provide a storage-state file created from your own authorized browser session.'
    ],
    events: events.slice(-50)
  };

  await writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify({ ...report, artifacts: { ...report.artifacts, report: reportPath } }, null, 2));

  await context.close();
  await browser.close();

  process.exitCode = ['reachable', 'client-error', 'server-error'].includes(report.classification) ? 0 : 2;
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack : String(err));
  process.exitCode = 1;
});
