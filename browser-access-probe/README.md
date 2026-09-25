# browser-access-probe

A Playwright-based browser access diagnostic tool that can reuse an **authorized local Chrome session**.

## Recommended mode: attach to local Chrome

This is the most useful mode for sites that reject fresh cloud/headless sessions.

### 1. Start a dedicated real Chrome session

```bash
cd browser-access-probe
npm install
npm run chrome
```

This launches the locally installed Google Chrome/Chromium with:

- a persistent profile under `.live-chrome-profile/`
- remote debugging bound to `127.0.0.1:9222`
- no proxy rotation, stealth patching, CAPTCHA solving, or fingerprint spoofing

Keep that Chrome window open.

### 2. Attach the probe to the exact same session

```bash
npm run attach -- "https://namu.wiki/w/%EC%9D%B4%EC%9E%AC%EB%AA%85%20%ED%94%BC%EC%8A%B5%20%EC%82%AC%EA%B1%B4"
```

The probe navigates the already-running Chrome tab and waits up to 180 seconds if the site asks for normal interactive verification. It does not click or solve the challenge itself. If the browser session becomes authorized normally, the probe detects the resulting navigation and records the rendered page.

Later runs reuse the same live Chrome profile automatically as long as you start it with `npm run chrome`.

## Persistent Playwright profile mode

A separate persistent Playwright-managed profile is still available:

```bash
npm run auto -- https://example.com
```

Visible browser using that profile:

```bash
npm run browser -- https://example.com
```

## Other modes

Temporary browser:

```bash
npm run probe -- https://example.com
```

Explicit storage state:

```bash
npm run probe -- https://example.com/account --storage-state state.json
```

Attach to a custom local CDP endpoint:

```bash
npm run probe -- https://example.com --cdp http://127.0.0.1:9222 --interactive-wait 180000
```

## Diagnostics

Every run records:

- main-document HTTP status
- final URL and title
- browser console/page errors
- failed requests
- common 403/429/challenge signals
- screenshot
- rendered HTML
- JSON report
- which session mode was used

### Result classes

- `reachable`
- `access-blocked`
- `rate-limited`
- `challenge-detected`
- `client-error`
- `server-error`
- `navigation-failed`

## Session safety

`.browser-profile/` and `.live-chrome-profile/` can contain authenticated browser state and must not be committed or shared.

The tool intentionally does **not** automate CAPTCHA solving, spoof browser fingerprints, rotate proxies, or otherwise defeat a site's access-control challenge.

## Verification

```bash
npm run check
npm test
```
