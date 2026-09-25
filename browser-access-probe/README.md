# browser-access-probe

A small Playwright-based diagnostic tool for checking whether a **public web page** is reachable through a normal Chromium session.

It is useful when a simple HTTP fetch gets blocked but a regular browser may still load the page because the site requires JavaScript, cookies, or an authenticated user session.

## What it does

- Opens the target with standard Playwright Chromium.
- Records the main HTTP status, final URL, page title, console/page errors, and failed requests.
- Detects common access-block/challenge signals such as HTTP 403/429 and generic CAPTCHA/challenge pages.
- Saves a screenshot, rendered HTML, and JSON report.
- Can reuse a Playwright `storageState` file from **your own authorized session**.

## What it intentionally does not do

- No CAPTCHA solving or challenge bypass.
- No stealth/fingerprint spoofing.
- No proxy rotation or IP evasion.
- No bypassing paywalls, authentication, robots-based restrictions, or other access controls.
- No local/private-network targets.

## Install

```bash
cd browser-access-probe
npm install
npx playwright install chromium
```

## Usage

```bash
npm run probe -- https://example.com
```

Visible browser:

```bash
npm run probe -- https://example.com --headed
```

Reuse your own authenticated Playwright session:

```bash
npm run probe -- https://example.com/account --storage-state state.json
```

Change output directory:

```bash
npm run probe -- https://example.com --out ./artifacts
```

The command prints a JSON summary and writes `PNG`, `HTML`, and `JSON` artifacts.

### Result classes

- `reachable` — page loaded without a detected challenge.
- `access-blocked` — HTTP access-control status such as 401/403/451.
- `rate-limited` — HTTP 429.
- `challenge-detected` — challenge/CAPTCHA-like content detected.
- `client-error` / `server-error` — ordinary 4xx/5xx response.
- `navigation-failed` — DNS, TLS, timeout, or other browser navigation failure.

## Tests

```bash
npm test
```
