import puppeteer from "puppeteer-core";

const browser = await puppeteer.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: "new",
  args: ["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 });
page.on("console", (msg) => console.log("console:", msg.type(), msg.text().slice(0, 160)));
page.on("pageerror", (err) => console.log("pageerror:", String(err).slice(0, 240)));
await page.goto("http://127.0.0.1:4173/", { waitUntil: "networkidle0", timeout: 60000 });
await new Promise((r) => setTimeout(r, 1200));
await page.screenshot({ path: "shots/ui-check-top.png" });
await page.evaluate(() => document.getElementById("consensus")?.scrollIntoView());
await new Promise((r) => setTimeout(r, 800));
await page.screenshot({ path: "shots/ui-check-consensus.png" });
await page.evaluate(() => document.getElementById("live")?.scrollIntoView());
await new Promise((r) => setTimeout(r, 800));
await page.screenshot({ path: "shots/ui-check-live.png" });
console.log("title:", await page.title());
console.log("body text length:", (await page.evaluate(() => document.body.innerText.length)));
await browser.close();
