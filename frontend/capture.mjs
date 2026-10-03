// Reproducible browser capture for the FairPay v0.4.1 milestone demo.
// Uses the system Google Chrome via puppeteer-core (no Chromium download).
//   node capture.mjs shots   -> writes shots/*.png still frames
//   node capture.mjs video    -> records a CDP screencast of the live UI, then
//                                ffmpeg assembles frames and burns in captions.
import { createRequire } from "module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");
const CHROME = process.env.CHROME || "/usr/bin/google-chrome";
const URL_ = process.env.APP_URL || "http://127.0.0.1:5173/";
const OUT = path.resolve("shots");
const FRAMES = path.join(OUT, "frames");
const FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf";
const TARGET_SECONDS = 48;

fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch(scale) {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--hide-scrollbars", `--force-device-scale-factor=${scale}`],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: scale });
  await page.goto(URL_, { waitUntil: "networkidle2" });
  return { browser, page };
}

async function waitLive(page) {
  await page.waitForFunction(() => /live on-chain read/.test(document.body.innerText), { timeout: 30000 });
}

async function shots() {
  const { browser, page } = await launch(2);
  await sleep(700);
  (await page.$("section:nth-of-type(1)")).screenshot({ path: path.join(OUT, "01_gateway_valid.png") });
  await page.click("#gateway-input", { clickCount: 3 });
  await page.type("#gateway-input", "https://ipfs.io.evil.com/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq", { delay: 10 });
  await sleep(400);
  (await page.$("section:nth-of-type(1)")).screenshot({ path: path.join(OUT, "02_gateway_lookalike.png") });
  await page.click('[data-tier="HIGH"]');
  await sleep(600);
  (await page.$("section:nth-of-type(2)")).screenshot({ path: path.join(OUT, "03_liability_high.png") });
  await waitLive(page);
  (await page.$("section:nth-of-type(3)")).screenshot({ path: path.join(OUT, "04_live_status.png") });
  await page.screenshot({ path: path.join(OUT, "00_full.png"), fullPage: true });
  await browser.close();
  console.log("shots written to", OUT);
}

// Smoothly set a range input's value and dispatch React's onChange.
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
        await new Promise((r) => setTimeout(r, 90));
      }
    },
    { selector, to, step }
  );
}

async function typeUrl(page, url) {
  await page.click("#gateway-input", { clickCount: 3 });
  await sleep(150);
  await page.keyboard.press("Backspace");
  await page.type("#gateway-input", url, { delay: 45 });
}

async function video() {
  fs.rmSync(FRAMES, { recursive: true, force: true });
  fs.mkdirSync(FRAMES, { recursive: true });
  const { browser, page } = await launch(1);
  await waitLive(page);

  // Real-time capture: grab a frame as fast as the page allows for the whole
  // scripted timeline, then play back at the measured wall-clock rate so the
  // motion is smooth and the duration is exactly how long the demo ran.
  let frames = 0;
  let recording = true;
  const captureLoop = (async () => {
    while (recording) {
      try {
        await page.screenshot({ path: path.join(FRAMES, `frame_${String(frames).padStart(5, "0")}.jpg`), type: "jpeg", quality: 72 });
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
  console.log(`timeline ran ${elapsed.toFixed(1)}s, captured ${frames} frames (~${(frames / elapsed).toFixed(1)} fps)`);
  await assemble(elapsed);
}

async function runTimeline(page) {
  await sleep(3200); // hero + valid default
  await page.click('[data-preset="Valid (Pinata)"]'); await sleep(1800);
  await typeUrl(page, "https://ipfs.io.evil.com/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq"); await sleep(3000);
  await page.click('[data-preset="Port smuggling"]'); await sleep(1800);
  await page.click('[data-preset="Not https"]'); await sleep(1700);
  await page.click('[data-preset="Extra path segment"]'); await sleep(1700);
  await page.click('[data-preset="Bad CID"]'); await sleep(1700);
  await page.click('[data-preset="Valid (ipfs.io)"]'); await sleep(2600); // back to green

  await page.evaluate(() => document.querySelectorAll("section")[1].scrollIntoView({ behavior: "smooth", block: "start" }));
  await sleep(1200);
  await slide(page, "#hours", 24);
  await slide(page, "#rate", 8);
  await sleep(800);
  await page.click('[data-tier="LOW"]'); await sleep(1600);
  await page.click('[data-tier="HIGH"]'); await sleep(1600);
  await page.click('[data-tier="MEDIUM"]'); await sleep(1600);

  await page.evaluate(() => document.querySelectorAll("section")[2].scrollIntoView({ behavior: "smooth", block: "start" }));
  await sleep(1200);
  await page.click("#job-id", { clickCount: 3 }); await page.type("#job-id", "1"); await page.click("#refresh-live");
  await waitLive(page); await sleep(2800);
  await page.click("#job-id", { clickCount: 3 }); await page.type("#job-id", "3"); await page.click("#refresh-live");
  await waitLive(page); await sleep(3400);
}

// Build the mp4 from the frames on shots/frames, played back in real time over
// `dur` seconds, then burn in captions. Split out so ffmpeg can re-run alone.
async function assemble(dur = TARGET_SECONDS) {
  const frames = fs.readdirSync(FRAMES).filter((f) => f.endsWith(".jpg")).length;
  const fps = +(frames / dur).toFixed(3);
  console.log(`assembling ${frames} frames -> fps ${fps}, duration ${dur.toFixed(1)}s`);

  const raw = path.join(OUT, "demo_raw.mp4");
  execFileSync("ffmpeg", ["-y", "-framerate", String(fps), "-i", path.join(FRAMES, "frame_%05d.jpg"),
    "-vf", "scale=1280:720:flags=lanczos,format=yuv420p", raw], { stdio: "inherit" });

  const caps = [
    { t: "v0.4.1: Real-time Multi-Gateway Validation", a: 0.0, b: 0.20 },
    { t: "Rejecting lookalike attack: ipfs.io.evil.com", a: 0.16, b: 0.33 },
    { t: "v0.4.0: Reserved Liability dynamically protects the budget", a: 0.5, b: 0.72 },
    { t: "Live on-chain state from StudioNet via gen_call", a: 0.78, b: 1.0 },
  ];
  caps.forEach((c, i) => fs.writeFileSync(path.join(OUT, `cap${i}.txt`), c.t));
  const filters = caps
    .map((c, i) => `drawtext=fontfile=${FONT}:textfile=${path.join(OUT, `cap${i}.txt`)}:fontcolor=white:fontsize=30:box=1:boxcolor=0x0b0a14@0.82:boxborderw=18:x=(w-text_w)/2:y=h-90:enable='between(t,${(c.a * dur).toFixed(2)},${(c.b * dur).toFixed(2)})'`)
    .join(",");
  const final = path.join(OUT, "fairpay_ui_demo.mp4");
  execFileSync("ffmpeg", ["-y", "-i", raw, "-vf", filters, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-movflags", "+faststart", final], { stdio: "inherit" });
  console.log("WROTE", final, `(${dur.toFixed(1)}s)`);
}

const mode = process.argv[2] || "shots";
const run = mode === "video" ? video : mode === "assemble" ? assemble : shots;
run().catch((e) => { console.error(e); process.exit(1); });
