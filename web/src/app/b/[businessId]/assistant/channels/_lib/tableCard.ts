/**
 * The printable table card: an A6 page (105 × 148 mm) with the business's
 * name, a heading and a line in the customers' language, the QR code and
 * the link under it for people who type it. It is a self-contained HTML
 * document (inline style and SVG, no scripts) shown in a frame as the
 * preview and printed from that frame.
 */

import { escapeXml, qrPath, qrSide, type QrMatrix } from "./qrCode";

export interface TableCard {
  businessName: string;
  /** The link the QR code opens, shown without "https://" under it. */
  linkText: string;
  matrix: QrMatrix;
  language: string;
  direction: "ltr" | "rtl";
  /** #rrggbb, else the cabinet's iris. */
  accent: string | null;
  heading: string;
  hint: string;
}

const DEFAULT_ACCENT = "#ad5732";
const ACCENT_PATTERN = /^#[0-9a-fA-F]{6}$/;

const CARD_STYLE = `
@page { size: 105mm 148mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Sans Georgian",
    "Noto Sans Armenian", "Noto Sans Hebrew", "Noto Sans Arabic", sans-serif;
  color: #111827;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.card {
  width: 105mm; height: 148mm; padding: 9mm 9mm 8mm;
  display: flex; flex-direction: column; align-items: center; text-align: center;
  overflow: hidden; break-inside: avoid;
}
.bar { width: 16mm; height: 1.6mm; border-radius: 1mm; background: var(--accent); margin-bottom: 5mm; }
.name { margin: 0; font-size: 19pt; line-height: 1.15; font-weight: 700; max-width: 100%; overflow-wrap: anywhere; }
.heading { margin: 4mm 0 0; font-size: 14pt; line-height: 1.25; font-weight: 600; color: var(--accent); }
.qr {
  margin-top: 5mm; width: 62mm; height: 62mm; padding: 2mm;
  border: 0.6mm solid var(--accent); border-radius: 4mm; background: #fff;
}
.qr svg { display: block; width: 100%; height: 100%; }
.hint { margin: 5mm 0 0; font-size: 10.5pt; line-height: 1.35; color: #374151; max-width: 80mm; }
.link { margin-top: auto; font-size: 8.5pt; color: #4b5563; direction: ltr; unicode-bidi: isolate; overflow-wrap: anywhere; }
`;

/** The card as an HTML document; every text is escaped. */
export function buildTableCardHtml(card: TableCard): string {
  const accent = card.accent && ACCENT_PATTERN.test(card.accent) ? card.accent : DEFAULT_ACCENT;
  const side = qrSide(card.matrix);
  const qr = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${side} ${side}" shape-rendering="crispEdges" aria-hidden="true">`,
    `<rect width="${side}" height="${side}" fill="#ffffff"/>`,
    `<path d="${qrPath(card.matrix)}" fill="#000000"/>`,
    "</svg>",
  ].join("");
  return [
    "<!doctype html>",
    `<html lang="${escapeXml(card.language)}" dir="${card.direction}">`,
    "<head>",
    '<meta charset="utf-8">',
    `<title>${escapeXml(card.businessName)}</title>`,
    `<style>:root { --accent: ${accent}; }${CARD_STYLE}</style>`,
    "</head>",
    "<body>",
    '<main class="card">',
    '<div class="bar"></div>',
    `<h1 class="name" dir="auto">${escapeXml(card.businessName)}</h1>`,
    `<p class="heading">${escapeXml(card.heading)}</p>`,
    `<div class="qr">${qr}</div>`,
    `<p class="hint">${escapeXml(card.hint)}</p>`,
    `<p class="link">${escapeXml(card.linkText)}</p>`,
    "</main>",
    "</body>",
    "</html>",
  ].join("");
}

/**
 * Print the document a frame shows (the card preview). False when the
 * browser refuses (no frame window, or printing is blocked).
 */
export function printFrame(frame: HTMLIFrameElement | null): boolean {
  const target = frame?.contentWindow;
  if (!target) {
    return false;
  }
  try {
    target.focus();
    target.print();
    return true;
  } catch {
    return false;
  }
}
