// Clean 1080p UI capture for the FairPay v0.4.1 demo (v3).
// Records the live UI with NO burned-in captions so a separate step can overlay
// the new educational subtitles. Uses system Google Chrome via puppeteer-core.
//   node capture_v3.mjs            -> shots/fairpay_ui_clean.mp4 (1920x1080, no captions)
import { createRequire } from "module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");
const CHROME = process.env.CHROME || "/usr/bin/google-chrome";
const URL_ = process.env.APP_URL || "http://127.0.0.1:5173/";
const OUT = path.resolve("shots");
const FRAMES = path.join(OUT, "frames3");
const TARGET_SECONDS = 75; // fixed output length so the caption timeline aligns

fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1"],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await page.goto(URL_, { waitUntil: "networkidle2" });
  return { browser, page };
}

async function waitLive(page) {
  await page.waitForFunction(() => /live on-chain read/.test(document.body.innerText), { timeout: 30000 });
}

async function slide(page, selector, to, step = 1) {
  await page.evaluate(
    async ({ selector, to, step }) => {
      const el = document.querySelector(selector);
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      const cur = Number(el.value);
      const dir = to > cur ? 1 : -1;
      for (let v = cur; dir > 0 ? v <= to : v >= to; v += dir * step) {
        setter.call(el, String(v));
        el.dispatchEvent(new Event("input", { bubbles: true }));
        await new Promise((r) => setTimeout(r, 70));
      }
    },
    { selector, to, step }
  );
}

async function typeUrl(page, url) {
  await page.click("#gateway-input", { clickCount: 3 });
  await sleep(150);
  await page.keyboard.press("Backspace");
  await page.type("#gateway-input", url, { delay: 55 });
}

async function scrollToSection(page, idx) {
  await page.evaluate((i) => document.querySelectorAll("section")[i].scrollIntoView({ behavior: "smooth", block: "start" }), idx);
}

// Scripted timeline aligned to the 8 educational caption windows (0-75s).
async function runTimeline(page) {
  // 0-5 title / hero (valid default already shown)
  await sleep(5000);
  // 5-15 Multi-Gateway Evidence Allowlist: cycle the valid gateways
  await page.click('[data-preset="Valid (ipfs.io)"]'); await sleep(3000);
  await page.click('[data-preset="Valid (Pinata)"]'); await sleep(3000);
  await page.click('[data-preset="Valid (ipfs.io)"]'); await sleep(4000);
  // 15-25 Strict URL Validation: reject malformed variants
  await page.click('[data-preset="Port smuggling"]'); await sleep(3000);
  await page.click('[data-preset="Not https"]'); await sleep(3500);
  await page.click('[data-preset="Extra path segment"]'); await sleep(3500);
  // 25-35 Lookalike Attack Prevention: type ipfs.io.evil.com (red REVERTED)
  await scrollToSection(page, 0); await sleep(600);
  await typeUrl(page, "https://ipfs.io.evil.com/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq");
  await sleep(6000);
  // 35-45 Content-Derived Integrity: back to a valid gateway (green)
  await page.click('[data-preset="Valid (ipfs.io)"]'); await sleep(8000);
  // 45-55 Reserved Liability Protection: calculator bars
  await scrollToSection(page, 1); await sleep(1200);
  await slide(page, "#hours", 24);
  await slide(page, "#rate", 8);
  await sleep(3000);
  // 55-65 Dynamic Budget Protection: tier changes move the protected headroom
  await page.click('[data-tier="LOW"]'); await sleep(3000);
  await page.click('[data-tier="HIGH"]'); await sleep(3500);
  await page.click('[data-tier="MEDIUM"]'); await sleep(3500);
  // 65-75 All Changes Verified: live on-chain reads
  await scrollToSection(page, 2); await sleep(1200);
  await page.click("#job-id", { clickCount: 3 }); await page.type("#job-id", "3"); await page.click("#refresh-live");
  await waitLive(page); await sleep(8800);
}

async function record() {
  fs.rmSync(FRAMES, { recursive: true, force: true });
  fs.mkdirSync(FRAMES, { recursive: true });
  const { browser, page } = await launch();
  await waitLive(page);

  let frames = 0;
  let recording = true;
  const captureLoop = (async () => {
    while (recording) {
      try {
        await page.screenshot({ path: path.join(FRAMES, `frame_${String(frames).padStart(5, "0")}.jpg`), type: "jpeg", quality: 82 });
        frames++;
      } catch { recording = false; }
    }
  })();

  const t0 = Date.now();
  await runTimeline(page);
  const elapsed = (Date.now() - t0) / 1000;
  recording = false;
  await captureLoop;
  await browser.close();
  console.log(`timeline ran ${elapsed.toFixed(1)}s, captured ${frames} frames`);

  // Assemble a clean 1080p mp4 fixed to TARGET_SECONDS (no captions).
  const fps = +(frames / TARGET_SECONDS).toFixed(3);
  const clean = path.join(OUT, "fairpay_ui_clean.mp4");
  execFileSync("ffmpeg", ["-y", "-framerate", String(fps), "-i", path.join(FRAMES, "frame_%05d.jpg"),
    "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-t", String(TARGET_SECONDS), clean], { stdio: "inherit" });
  console.log("WROTE", clean, `(${TARGET_SECONDS}s, 1920x1080, no captions)`);
}

record().catch((e) => { console.error(e); process.exit(1); });
