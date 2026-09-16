import { chromium } from 'playwright';

const baseURL = process.env.BASE_URL || 'http://127.0.0.1:4173';
const screenshotPath = process.env.SMOKE_SCREENSHOT || 'smoke-home.png';
const assetOrigin = 'https://seven-prince-assets.vercel.app';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const pageErrors = [];

page.on('pageerror', (error) => pageErrors.push(error.message));

// The production asset service only allows selected browser origins.
// For CI we proxy those exact upstream responses through Playwright and
// only relax CORS locally, so the test still uses the real manifest/images.
await page.route(`${assetOrigin}/**`, async (route) => {
  const upstream = await route.fetch();
  const headers = {
    ...upstream.headers(),
    'access-control-allow-origin': '*',
  };
  await route.fulfill({ response: upstream, headers });
});

try {
  const response = await page.goto(`${baseURL}/index.html`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  if (!response || !response.ok()) {
    throw new Error(`index.html failed to load: ${response?.status() ?? 'no response'}`);
  }

  await page.waitForSelector('#homePage.active', { timeout: 15000 });
  await page.waitForFunction(() => {
    const logo = document.querySelector('#homeLogo');
    return logo && logo.complete && logo.naturalWidth > 0;
  }, null, { timeout: 20000 });

  await page.click('#openComicMenu');
  await page.waitForSelector('#menuPage.active', { timeout: 10000 });

  const chapterButtons = page.locator('#chocolateGrid button.active-cell');
  const chapterCount = await chapterButtons.count();
  if (chapterCount < 3) {
    throw new Error(`expected at least 3 comic chapter buttons, found ${chapterCount}`);
  }

  const chapter219 = page.getByRole('button', { name: '219화 보기' });
  if ((await chapter219.count()) !== 1) {
    throw new Error('219화 보기 button was not found');
  }

  await chapter219.click();
  await page.waitForSelector('#viewerPage.active', { timeout: 10000 });
  await page.waitForFunction(() => {
    const image = document.querySelector('#viewerImage');
    return image && image.style.display !== 'none' && image.complete && image.naturalWidth > 0;
  }, null, { timeout: 20000 });

  if (pageErrors.length) {
    throw new Error(`browser JavaScript errors:\n${pageErrors.join('\n')}`);
  }

  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log('Smoke test passed: real assets, home, menu, and 219 viewer are working.');
} catch (error) {
  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
