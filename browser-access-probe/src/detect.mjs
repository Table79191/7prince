const BLOCK_TITLE_PATTERNS = [
  /access denied/i,
  /forbidden/i,
  /just a moment/i,
  /attention required/i,
  /verify (you are|that you are) human/i,
  /captcha/i,
  /too many requests/i
];

const BLOCK_BODY_PATTERNS = [
  /access denied/i,
  /request blocked/i,
  /temporarily blocked/i,
  /unusual traffic/i,
  /verify (you are|that you are) human/i,
  /checking your browser/i,
  /enable javascript and cookies/i,
  /captcha/i,
  /rate limit/i,
  /too many requests/i
];

export function validateTarget(raw) {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`Invalid URL: ${raw}`);
  }

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('Only http:// and https:// URLs are supported.');
  }

  const host = url.hostname.toLowerCase();
  const blockedHosts = new Set(['localhost', '127.0.0.1', '::1']);
  if (blockedHosts.has(host) || host.endsWith('.local')) {
    throw new Error('Local/private targets are intentionally unsupported.');
  }

  return url;
}

export function classifyResponse({ status, title = '', bodyText = '' }) {
  const signals = [];

  if ([401, 403, 407, 423, 429, 451, 503].includes(status)) {
    signals.push(`http:${status}`);
  }
  if (BLOCK_TITLE_PATTERNS.some((p) => p.test(title))) {
    signals.push('title:challenge-or-block');
  }
  if (BLOCK_BODY_PATTERNS.some((p) => p.test(bodyText.slice(0, 20000)))) {
    signals.push('body:challenge-or-block');
  }

  let classification = 'reachable';
  if (status === 429) classification = 'rate-limited';
  else if ([401, 403, 407, 423, 451].includes(status)) classification = 'access-blocked';
  else if (signals.some((s) => s.includes('challenge-or-block'))) classification = 'challenge-detected';
  else if (status >= 500) classification = 'server-error';
  else if (status >= 400) classification = 'client-error';

  return { classification, signals };
}
