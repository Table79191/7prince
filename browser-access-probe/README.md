# browser-access-probe

A Playwright-based browser access diagnostic tool that can retain an **authorized local Chromium profile** between runs.

## Automatic session reuse

The project now has a persistent-profile mode. Cookies, local storage, and other ordinary Chromium session state are stored under `.browser-profile/` and automatically reused.

Install once:

```bash
cd browser-access-probe
npm install
npx playwright install chromium
```

Automatic access with the saved profile:

```bash
npm run auto -- https://example.com
```

For the NamuWiki page:

```bash
npm run auto -- "https://namu.wiki/w/%EC%9D%B4%EC%9E%AC%EB%AA%85%20%ED%94%BC%EC%8A%B5%20%EC%82%AC%EA%B1%B4"
```

If that site requires a fresh interactive verification, open the **same persistent profile** visibly:

```bash
npm run browser -- "https://namu.wiki/w/%EC%9D%B4%EC%9E%AC%EB%AA%85%20%ED%94%BC%EC%8A%B5%20%EC%82%AC%EA%B1%B4"
```

After a normal authorized browser session exists, later `npm run auto -- URL` calls reuse it automatically.

## Other modes

Temporary browser session:

```bash
npm run probe -- https://example.com
```

Explicit Playwright storage state:

```bash
npm run probe -- https://example.com/account --storage-state state.json
```

Custom persistent profile:

```bash
npm run probe -- https://example.com --profile-dir ./my-profile
```

## Diagnostics

Every run records:

- main HTTP status and final URL
- page title
- console/page errors and failed requests
- common 403/429/challenge signals
- screenshot
- rendered HTML
- JSON report

### Result classes

- `reachable`
- `access-blocked`
- `rate-limited`
- `challenge-detected`
- `client-error`
- `server-error`
- `navigation-failed`

## Safety boundaries

The persistent profile is ordinary browser session reuse. The tool intentionally does **not** solve CAPTCHAs, spoof browser fingerprints, rotate proxies, or defeat a site's access-control challenge.

The `.browser-profile/` directory is ignored by Git and should never be committed because it can contain authenticated browser data.

## Tests

```bash
npm test
```
