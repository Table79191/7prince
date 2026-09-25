#!/usr/bin/env node
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { classifyResponse, validateTarget } from './detect.mjs';
import { buildPublicFallbacks, isBlockedClassification } from './fallbacks.mjs';

function parseArgs(argv) {
  const args = {
    headed: false,
    outDir: 'artifacts',
    profileDir: undefined,
    storageState: undefined,
    cdpEndpoint: undefined,
    interactiveWaitMs: 0,
    timeoutMs: 30000,
    waitMs: 1500,
    publicFallbacks: true
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--headed') args.headed = true;
    else if (a === '--no-public-fallbacks') args.publicFallbacks = false;
    else if (a === '--out' && argv[i + 1]) args.outDir = argv[++i];
    else if (a === '--profile-dir' && argv[i + 1]) args.profileDir = argv[++i];
    else if (a === '--storage-state' && argv[i + 1]) args.storageState = argv[++i];
    else if (a === '--cdp' && argv[i + 1]) args.cdpEndpoint = argv[++i];
    else if (a === '--interactive-wait' && argv[i + 1]) args.interactiveWaitMs = Number(argv[++i]);
    else if (a === '--timeout' && argv[i + 1]) args.timeoutMs = Number(argv[++i]);
    else if (a === '--wait' && argv[i + 1]) args.waitMs = Number(argv[++i]);
    else if (!args.url) args.url = a;
    else throw new Error(`Unknown argument: ${a}`);
  }

  if (!args.url) {
    throw new Error('Usage: npm run probe -- <url> [--headed] [--profile-dir dir] [--storage-state state.json] [--cdp endpoint] [--interactive-wait ms] [--no-public-fallbacks] [--out artifacts]');
  }

  const sessionModes = [args.profileDir, args.storageState, args.cdpEndpoint].filter(Boolean);
  if (sessionModes.length > 1) {
    throw new Error('Use only one of --profile-dir, --storage-state, or --cdp.');
  }

  if (!Number.isFinite(args.timeoutMs) || args.timeoutMs < 1000 || args.timeoutMs > 120000) {
    throw new Error('--timeout must be between 1000 and 120000 ms.');
  }
  if (!Number.isFinite(args.waitMs) || args.waitMs < 0 || args.waitMs > 10000) {
    throw new Error('--wait must be between 0 and 10000 ms.');
  }
  if (!Number.isFinite(args.interactiveWaitMs) || args.interactiveWaitMs < 0 || args.interactiveWaitMs > 600000) {
    throw new Error('--interactive-wait must be between 0 and 600000 ms.');
  }

  return args;
}

function safeStamp() {
  return new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-');
}

async function pageSnapshot(page, status) {
  const finalUrl = page.url();
  const title = await page.title().catch(() => '');
  const bodyText = await page.locator('body').innerText({ timeout: 3000 }).catch(() => '');
  const html = await page.content().catch(() => '');
  const verdict = classifyResponse({ status, title, bodyText });
  return { status, finalUrl, title, bodyText, html, verdict };
}

async function waitForInteractiveAccess(page, getStatus, waitMs) {
  if (!waitMs) return null;

  const started = Date.now();
  while (Date.now() - started < waitMs) {
    await page.waitForTimeout(1000);
    const snap = await pageSnapshot(page, getStatus());
    const blocked = isBlockedClassification(snap.verdict.classification);
    if (!blocked && snap.status > 0 && snap.status < 400) {
      return snap;
    }
  }
  return null;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const target = validateTarget(args.url);
  const outDir = path.resolve(args.outDir);
  await mkdir(outDir, { recursive: true });

  let browser;
  let context;
  let attachedOverCdp = false;
  let launchedBrowser = false;

  if (args.cdpEndpoint) {
    browser = await chromium.connectOverCDP(args.cdpEndpoint);
    attachedOverCdp = true;
    context = browser.contexts()[0];
    if (!context) throw new Error('The attached Chrome instance has no browser context.');
  } else if (args.profileDir) {
    const profileDir = path.resolve(args.profileDir);
    await mkdir(profileDir, { recursive: true });
    context = await chromium.launchPersistentContext(profileDir, {
      headless: !args.headed,
      locale: 'ko-KR'
    });
  } else {
    browser = await chromium.launch({ headless: !args.headed });
    launchedBrowser = true;
    context = await browser.newContext({
      storageState: args.storageState,
      locale: 'ko-KR'
    });
  }

  const pages = context.pages();
  const page = pages[0] ?? await context.newPage();

  const events = [];
  let latestMainStatus = 0;

  page.on('console', (msg) => events.push({ type: 'console', level: msg.type(), text: msg.text() }));
  page.on('pageerror', (err) => events.push({ type: 'pageerror', text: err.message }));
  page.on('requestfailed', (req) => events.push({ type: 'requestfailed', url: req.url(), error: req.failure()?.errorText }));
  page.on('response', (res) => {
    try {
      if (res.request().isNavigationRequest() && res.frame() === page.mainFrame()) {
        latestMainStatus = res.status();
      }
    } catch {}
  });

  const started = Date.now();
  const attempts = [];

  async function navigate(candidate, kind) {
    latestMainStatus = 0;
    let navigationError = null;
    let response;

    try {
      response = await page.goto(candidate.href, {
        waitUntil: 'domcontentloaded',
        timeout: args.timeoutMs
      });
      latestMainStatus = response?.status() ?? latestMainStatus;
      if (args.waitMs) await page.waitForTimeout(args.waitMs);
    } catch (err) {
      navigationError = err instanceof Error ? err.message : String(err);
    }

    const snap = await pageSnapshot(page, latestMainStatus);
    if (navigationError && snap.status === 0) snap.verdict.classification = 'navigation-failed';

    attempts.push({
      kind,
      url: candidate.href,
      finalUrl: snap.finalUrl,
      status: snap.status,
      title: snap.title,
      classification: snap.verdict.classification,
      navigationError
    });

    return { snap, navigationError, candidate, kind };
  }

  let result = await navigate(target, 'original');
  const fallbacks = args.publicFallbacks ? buildPublicFallbacks(target) : [];

  if (isBlockedClassification(result.snap.verdict.classification)) {
    for (const fallback of fallbacks) {
      const candidateResult = await navigate(fallback, 'public-mirror');
      result = candidateResult;
      if (!isBlockedClassification(candidateResult.snap.verdict.classification) && candidateResult.snap.status > 0 && candidateResult.snap.status < 400) {
        break;
      }
    }
  }

  if (attachedOverCdp && isBlockedClassification(result.snap.verdict.classification) && args.interactiveWaitMs > 0) {
    result = await navigate(target, 'original-interactive');
    console.error('\nThe attached Chrome tab is waiting for normal site verification. No challenge interaction is automated.');
    const recovered = await waitForInteractiveAccess(page, () => latestMainStatus, args.interactiveWaitMs);
    if (recovered) {
      result = {
        ...result,
        snap: recovered
      };
      attempts.push({
        kind: 'interactive-result',
        url: target.href,
        finalUrl: recovered.finalUrl,
        status: recovered.status,
        title: recovered.title,
        classification: recovered.verdict.classification,
        navigationError: null
      });
    }
  }

  const snap = result.snap;
  const stamp = safeStamp();
  const shotPath = path.join(outDir, `probe-${stamp}.png`);
  const htmlPath = path.join(outDir, `probe-${stamp}.html`);
  const reportPath = path.join(outDir, `probe-${stamp}.json`);

  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});
  await writeFile(htmlPath, snap.html, 'utf8');

  const sessionMode = attachedOverCdp
    ? 'cdp-attached-chrome'
    : args.profileDir
      ? 'persistent-profile'
      : args.storageState
        ? 'storage-state'
        : 'temporary';

  const usedPublicMirror = result.kind === 'public-mirror';
  const report = {
    requestedUrl: target.href,
    resolvedUrl: result.candidate.href,
    finalUrl: snap.finalUrl,
    status: snap.status,
    title: snap.title,
    classification: snap.verdict.classification,
    signals: snap.verdict.signals,
    navigationError: result.navigationError,
    elapsedMs: Date.now() - started,
    source: {
      kind: usedPublicMirror ? 'public-mirror' : 'original',
      mirroredFrom: usedPublicMirror ? target.href : null,
      sameDocumentPath: usedPublicMirror ? new URL(result.candidate.href).pathname === target.pathname : true
    },
    attempts,
    session: {
      mode: sessionMode,
      profileDir: args.profileDir ? path.resolve(args.profileDir) : null,
      cdpEndpoint: attachedOverCdp ? args.cdpEndpoint : null
    },
    artifacts: { screenshot: shotPath, html: htmlPath },
    notes: [
      usedPublicMirror
        ? 'The original host was unavailable, so the same public document path was loaded from a public mirror.'
        : 'The original host supplied the final page.',
      'Public mirrors are third-party copies and may lag behind the original; verify important facts against primary/reliable sources.',
      'This tool does not solve CAPTCHAs, spoof browser fingerprints, rotate proxies, or bypass access controls.'
    ],
    events: events.slice(-50)
  };

  await writeFile(reportPath, JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify({ ...report, artifacts: { ...report.artifacts, report: reportPath } }, null, 2));

  const exitCode = ['reachable', 'client-error', 'server-error'].includes(report.classification) ? 0 : 2;

  if (attachedOverCdp) {
    process.exit(exitCode);
  }

  await context.close().catch(() => {});
  if (launchedBrowser && browser) await browser.close().catch(() => {});
  process.exitCode = exitCode;
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack : String(err));
  process.exitCode = 1;
});
