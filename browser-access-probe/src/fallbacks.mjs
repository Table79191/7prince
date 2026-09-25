export function buildPublicFallbacks(target) {
  const url = target instanceof URL ? target : new URL(target);
  const host = url.hostname.toLowerCase();

  if (host !== 'namu.wiki' && host !== 'www.namu.wiki') return [];

  return ['d.namu.moe', 'www.namu.moe', 'm.namu.moe'].map((fallbackHost) => {
    const candidate = new URL(url.href);
    candidate.hostname = fallbackHost;
    candidate.protocol = 'https:';
    candidate.port = '';
    return candidate;
  });
}

export function isBlockedClassification(classification) {
  return ['access-blocked', 'challenge-detected', 'rate-limited', 'navigation-failed'].includes(classification);
}
