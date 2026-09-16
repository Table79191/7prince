import { chromium } from 'playwright';

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:4173';
const screenshotPath = process.env.SMOKE_SCREENSHOT || 'smoke-home.png';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const pageErrors = [];

page.on('pageerror', (error) => pageErrors.push(error.message));

try {
  const manifestResponsePromise = page.waitForResponse(
    (response) => {
      try {
        const url = new URL(response.url());
        return url.pathname.endsWith('/manifest');
      } catch {
        return false;
      }
    },
    { timeout: 30000 },
  );

  const response = await page.goto(`${baseURL}/index.html`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  if (!response || !response.ok()) {
    throw new Error(`index.html failed to load: ${response?.status() ?? 'no response'}`);
  }

  const manifestResponse = await manifestResponsePromise;
  if (!manifestResponse.ok()) {
    throw new Error(`manifest request failed: ${manifestResponse.status()}`);
  }

  await page.waitForSelector('#homePage.active', { timeout: 15000 });
  await page.waitForFunction(() => {
    const logo = document.querySelector('#homeLogo');
    return logo && logo.complete && logo.naturalWidth > 0;
  }, { timeout: 20000 });

  await page.screenshot({ path: screenshotPath, fullPage: true });

  await page.click('#openComicMenu');
  await page.waitForSelector('#menuPage.active', { timeout: 10000 });

  const chapterButtons = page.locator('#chocolateGrid button.active-cell');
  const chapterCount = await chapterButtons.count();
  if (chapterCount < 3) {
    throw new Error(`expected at least 3 comic chapter buttons, found ${chapterCount}`);
  }

  const chapter219 = page.getByRole('button', { name: '219화 보기' });
  if (await chapter219.count()) {
    await chapter219.click();
    await page.waitForSelector('#viewerPage.active', { timeout: 10000 });
    await page.waitForFunction(() => {
      const image = document.querySelector('#viewerImage');
      return image && image.style.display !== 'none' && image.complete && image.naturalWidth > 0;
    }, { timeout: 20000 });
  }

  if (pageErrors.length) {
    throw new Error(`browser JavaScript errors:\n${pageErrors.join('\n')}`);
  }

  console.log('Smoke test passed: manifest, home, menu, and comic viewer are working.');
} finally {
  await browser.close();
}
