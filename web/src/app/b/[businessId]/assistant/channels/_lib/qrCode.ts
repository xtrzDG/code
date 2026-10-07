/**
 * QR codes of share links, made in the browser (uqr; nothing is sent
 * anywhere): the module grid, an SVG of it and a PNG for download.
 * Error correction M (15 %) survives a little dirt or a crease on a
 * printed card; the quiet zone is the standard four modules.
 */

import { encode } from "uqr";

export interface QrMatrix {
  /** Modules per side, without the quiet zone. */
  size: number;
  /** `modules[y][x]` is true for a dark module. */
  modules: boolean[][];
}

export const QUIET_ZONE = 4;
/** Pixels per module of a downloaded PNG (a 33-module code: 656 px). */
const PNG_MODULE_PIXELS = 16;

export function encodeQr(text: string): QrMatrix {
  const result = encode(text, { ecc: "M", border: 0 });
  return { size: result.size, modules: result.data };
}

/** Modules per side with the quiet zone. */
export function qrSide(matrix: QrMatrix): number {
  return matrix.size + 2 * QUIET_ZONE;
}

/** One SVG path of the dark modules (runs in a row merged), in module units with the quiet zone. */
export function qrPath(matrix: QrMatrix): string {
  const parts: string[] = [];
  matrix.modules.forEach((row, y) => {
    let x = 0;
    while (x < row.length) {
      if (!row[x]) {
        x += 1;
        continue;
      }
      const start = x;
      while (x < row.length && row[x]) {
        x += 1;
      }
      const run = x - start;
      parts.push(`M${start + QUIET_ZONE} ${y + QUIET_ZONE}h${run}v1h-${run}z`);
    }
  });
  return parts.join("");
}

/** A standalone SVG file: black on white, any size (vector). */
export function qrSvgDocument(matrix: QrMatrix, title: string): string {
  const side = qrSide(matrix);
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${side} ${side}" width="${side * 8}" height="${side * 8}" shape-rendering="crispEdges">`,
    `<title>${escapeXml(title)}</title>`,
    `<rect width="${side}" height="${side}" fill="#ffffff"/>`,
    `<path d="${qrPath(matrix)}" fill="#000000"/>`,
    "</svg>",
  ].join("");
}

/** The code drawn on a canvas, `PNG_MODULE_PIXELS` per module. */
export function drawQr(matrix: QrMatrix, canvas: HTMLCanvasElement, modulePixels = PNG_MODULE_PIXELS): void {
  const side = qrSide(matrix) * modulePixels;
  canvas.width = side;
  canvas.height = side;
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, side, side);
  context.fillStyle = "#000000";
  matrix.modules.forEach((row, y) => {
    row.forEach((isDark, x) => {
      if (isDark) {
        context.fillRect((x + QUIET_ZONE) * modulePixels, (y + QUIET_ZONE) * modulePixels, modulePixels, modulePixels);
      }
    });
  });
}

export function qrPngBlob(matrix: QrMatrix): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  drawQr(matrix, canvas);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

/** Save a blob under a file name (an object URL on a temporary link). */
export function saveBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
