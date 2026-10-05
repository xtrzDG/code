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
 *   src/app/favicon.ico                            16, 32 and 48 px PNGs in one ICO (what
 *                                                  browsers fetch at /favicon.ico by themselves)
 *
 *   npm run gen:icons
 *   PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome npm run gen:icons
 *
 * Run it after changing icon.svg and commit the PNG files.
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const WEB_DIRECTORY = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const MARK = readFileSync(path.join(WEB_DIRECTORY, "src/app/icon.svg"), "utf8");
const ACCENT = /fill="(#[0-9a-fA-F]{6})"/.exec(MARK)?.[1] ?? "#ad5732";
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

const FAVICON_FILE = "src/app/favicon.ico";
const FAVICON_SIZES = [16, 32, 48];

/** An ICO file holding PNG images (Windows Vista+ and every browser read PNG entries). */
function icoFromPngs(images) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = 6 + 16 * images.length;
  const entries = images.map(({ size, data }) => {
    const entry = Buffer.alloc(16);
    entry.writeUInt8(size >= 256 ? 0 : size, 0);
    entry.writeUInt8(size >= 256 ? 0 : size, 1);
    entry.writeUInt16LE(1, 4);
    entry.writeUInt16LE(32, 6);
    entry.writeUInt32LE(data.length, 8);
    entry.writeUInt32LE(offset, 12);
    offset += data.length;
    return entry;
  });
  return Buffer.concat([header, ...entries, ...images.map((image) => image.data)]);
}

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
  const favicons = [];
  for (const size of FAVICON_SIZES) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><html><body style="margin:0;background:transparent">${plain(size)}</body></html>`);
    favicons.push({ size, data: await page.screenshot({ omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } }) });
    await page.close();
  }
  writeFileSync(path.join(WEB_DIRECTORY, FAVICON_FILE), icoFromPngs(favicons));
  process.stdout.write(`${FAVICON_FILE} (${FAVICON_SIZES.join(", ")})\n`);
} finally {
  await browser.close();
}
