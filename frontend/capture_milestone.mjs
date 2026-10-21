// Capture the Milestone v1 UI for the 48s demo.
//
// The preview server must be running at http://127.0.0.1:4173. Frames are
// scheduled by frame index, so the resulting 15 fps sequence always maps to the
// 48 second timeline even if a screenshot takes slightly longer than real time.
import fs from "node:fs";
import puppeteer from "puppeteer-core";

const OUT = "shots/milestone_frames";
const FPS = 15;
const SECONDS = 48;
const TOTAL = FPS * SECONDS;

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function scrollTo(page, id) {
  await page.evaluate((sectionId) => {
    const el = document.getElementById(sectionId);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 88;
    window.scrollTo({ top, behavior: "smooth" });
  }, id);
}

async function setRange(page, selector, value) {
  await page.evaluate(
    ({ selector, value }) => {
      const el = document.querySelector(selector);
      if (!el) return;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      ).set;
      setter.call(el, String(value));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    },
    { selector, value },
  );
}

async function setRangeAt(page, selector, index, value) {
  await page.evaluate(
    ({ selector, index, value }) => {
      const el = document.querySelectorAll(selector)[index];
      if (!el) return;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      ).set;
      setter.call(el, String(value));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    },
    { selector, index, value },
  );
}

async function clickText(page, selector, text) {
  return page.evaluate(
    ({ selector, text }) => {
      const nodes = Array.from(document.querySelectorAll(selector));
      const el = nodes.find((node) => node.innerText.trim().includes(text));
      if (!el) return false;
      el.click();
      return true;
    },
    { selector, text },
  );
}

async function clickAnchor(page, value) {
  return page.evaluate((value) => {
    const buttons = Array.from(document.querySelectorAll("#simulator button"));
    const el = buttons.find(
      (node) => node.innerText.split("\n")[0].trim() === String(value),
    );
    if (!el) return false;
    el.click();
    return true;
  }, value);
}

async function act(page, frame) {
  // 0-6 hero. 6-12 simulator. 12-18 PAPITO lock. 18-24 timeline.
  // 24-30 consensus. 30-36 guard lab. 36-42 live reads. 42-48 outro.
  if (frame === 75) await scrollTo(page, "simulator");
  if (frame === 90) {
    await setRangeAt(page, "#simulator input[type=range]", 0, 70);
    await setRangeAt(page, "#simulator input[type=range]", 1, 20);
  }
  if (frame === 112) await clickAnchor(page, 0);
  if (frame === 128) await clickAnchor(page, 50);
  if (frame === 143) await clickAnchor(page, 80);
  if (frame === 165) await clickText(page, "#simulator button", "Simulate settlement");
  if (frame === 263) await scrollTo(page, "timeline");
  if (frame === 273) await clickText(page, "#timeline button", "Reset");
  if (frame === 282) await clickText(page, "#timeline button", "Advance");
  if (frame === 293) await clickText(page, "#timeline button", "Advance");
  if (frame === 308) await clickText(page, "#timeline button", "Appeal");
  if (frame === 320) await clickText(page, "#timeline button", "Advance");
  if (frame === 353) await scrollTo(page, "consensus");
  if (frame === 368) await setRange(page, "#consensus input[type=range]", 100);
  if (frame === 390) await clickText(page, "#consensus button", "Open prompt drawer");
  if (frame === 428) await page.evaluate(() => {
    const el = document.querySelector('[aria-label="Close inspector"]');
    if (el) el.click();
  });
  if (frame === 435) await setRange(page, "#consensus input[type=range]", 50);
  if (frame === 443) await scrollTo(page, "guard-lab");
  if (frame === 458) await clickText(page, "#guard-lab button", "Premature surplus");
  if (frame === 483) await clickText(page, "#guard-lab button", "Single-party");
  if (frame === 510) await clickText(page, "#guard-lab button", "Post-settlement");
  if (frame === 537) await scrollTo(page, "live");
  if (frame === 600) await clickText(page, "#live button", "Refresh");
  if (frame === 630) await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
}

const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
page.on("pageerror", (err) => console.log("pageerror:", String(err).slice(0, 200)));
await page.goto("http://127.0.0.1:4173/", { waitUntil: "networkidle0", timeout: 90000 });
await page.waitForFunction(() => document.body.innerText.includes("VAULT INVARIANT"), {
  timeout: 30000,
}).catch(() => console.log("live panel not ready; capturing anyway"));
await sleep(1500);

const start = Date.now();
for (let frame = 0; frame < TOTAL; frame += 1) {
  const target = start + (frame * 1000) / FPS;
  const wait = target - Date.now();
  if (wait > 0) await sleep(wait);
  await act(page, frame);
  await page.screenshot({
    path: `${OUT}/${String(frame).padStart(5, "0")}.jpg`,
    type: "jpeg",
    quality: 88,
  });
  if (frame % 75 === 0) console.log("frame", frame, "of", TOTAL);
}
await browser.close();
console.log("captured", TOTAL, "frames at", FPS, "fps");
