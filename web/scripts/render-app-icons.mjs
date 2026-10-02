#!/usr/bin/env node
/**
 * The installed app's icons, drawn from the product mark (src/app/icon.svg)
 * in Chromium and saved as PNG (browsers and phones want raster icons):
 *
 *   public/icons/icon-192.png, icon-512.png        the mark as it is ("any")
 *   public/icons/maskable-192.png, maskable-512.png the sparkles inside the safe
 *                                                  zone on a full colour square
 *                                                  (Android crops it to its shape)
 *   src/app/apple-icon.png                         180 × 180, opaque (iOS home screen)
 *
 *   npm run gen:icons
 *   PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome npm run gen:icons
 *
 * Run it after changing icon.svg and commit the PNG files.
 */

import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const WEB_DIRECTORY = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const MARK = readFileSync(path.join(WEB_DIRECTORY, "src/app/icon.svg"), "utf8");
const ACCENT = /fill="(#[0-9a-fA-F]{6})"/.exec(MARK)?.[1] ?? "#4f46e5";
// The sparkles alone (the mark without its rounded square), for the maskable icons.
const SPARKLES = MARK.replace(/<rect[^>]*\/>/, "").replace(/viewBox="0 0 32 32"/, 'viewBox="4 5 24 24"');

/** Full-bleed accent square with the sparkles in the middle 60 % (the maskable safe zone is 80 %). */
const maskable = (size) => `
  <div style="width:${size}px;height:${size}px;background:${ACCENT};display:grid;place-items:center">
    <div style="width:${Math.round(size * 0.6)}px;height:${Math.round(size * 0.6)}px">${SPARKLES.replace("<svg ", '<svg width="100%" height="100%" ')}</div>
  </div>`;
const plain = (size) => `<div style="width:${size}px;height:${size}px">${MARK.replace("<svg ", '<svg width="100%" height="100%" ')}</div>`;

const ICONS = [
  { file: "public/icons/icon-192.png", size: 192, html: plain(192), transparent: true },
  { file: "public/icons/icon-512.png", size: 512, html: plain(512), transparent: true },
  { file: "public/icons/maskable-192.png", size: 192, html: maskable(192), transparent: false },
  { file: "public/icons/maskable-512.png", size: 512, html: maskable(512), transparent: false },
  { file: "src/app/apple-icon.png", size: 180, html: maskable(180), transparent: false },
];

const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined });
try {
  for (const icon of ICONS) {
    const page = await browser.newPage({ viewport: { width: icon.size, height: icon.size }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><html><body style="margin:0;background:transparent">${icon.html}</body></html>`);
    const target = path.join(WEB_DIRECTORY, icon.file);
    mkdirSync(path.dirname(target), { recursive: true });
    await page.screenshot({ path: target, omitBackground: icon.transparent, clip: { x: 0, y: 0, width: icon.size, height: icon.size } });
    await page.close();
    process.stdout.write(`${icon.file} (${icon.size} × ${icon.size})\n`);
  }
} finally {
  await browser.close();
}
