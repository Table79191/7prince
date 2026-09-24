import { chromium } from "playwright";

const base = process.env.VIEWER_URL || "http://127.0.0.1:8765/index.html";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

let embedRequest = null;
page.on("request", request => {
  if (request.url().includes("youtube-nocookie.com/embed/NNyJmOhbVXU")) {
    embedRequest = request;
  }
});

await page.goto(base + "?url=" + encodeURIComponent("https://youtu.be/NNyJmOhbVXU?si=test"), {
  waitUntil: "domcontentloaded"
});

const iframeSrc = await page.locator("iframe").getAttribute("src");
if (!iframeSrc || !iframeSrc.includes("/embed/NNyJmOhbVXU")) {
  throw new Error("YouTube embed was not created correctly: " + iframeSrc);
}

await page.waitForTimeout(1000);

if (!embedRequest) {
  throw new Error("YouTube embed network request was not observed");
}

const referer = embedRequest.headers()["referer"] || "";
if (!referer.startsWith("http://127.0.0.1:8765/")) {
  throw new Error("YouTube embed request is missing local HTTP Referer: " + referer);
}

const ytMode = await page.locator("#mode").textContent();
if (!ytMode.includes("YouTube")) throw new Error("YouTube mode label missing");

await page.goto(base + "?url=" + encodeURIComponent("https://example.com/sample.mp4"), {
  waitUntil: "domcontentloaded"
});
const videoSrc = await page.locator("video").getAttribute("src");
if (videoSrc !== "https://example.com/sample.mp4") {
  throw new Error("Direct video source mismatch: " + videoSrc);
}

const directMode = await page.locator("#mode").textContent();
if (!directMode.includes("Direct media")) throw new Error("Direct mode label missing");

await browser.close();
console.log("VIEWER BROWSER TEST OK");
