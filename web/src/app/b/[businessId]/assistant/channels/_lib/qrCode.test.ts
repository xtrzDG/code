import jsQR from "jsqr";
import { afterEach, describe, expect, it, vi } from "vitest";

import { drawQr, encodeQr, escapeXml, qrPath, qrPngBlob, qrSide, qrSvgDocument, QUIET_ZONE, saveBlob, type QrMatrix } from "./qrCode";

const PIXELS = 4;

/** The code as a white-and-black RGBA image, the way a camera would see a print. */
function rasterize(matrix: QrMatrix): { data: Uint8ClampedArray; side: number } {
  const side = qrSide(matrix) * PIXELS;
  const data = new Uint8ClampedArray(side * side * 4).fill(255);
  matrix.modules.forEach((row, y) => {
    row.forEach((isDark, x) => {
      if (!isDark) {
        return;
      }
      for (let dy = 0; dy < PIXELS; dy += 1) {
        for (let dx = 0; dx < PIXELS; dx += 1) {
          const offset = (((y + QUIET_ZONE) * PIXELS + dy) * side + (x + QUIET_ZONE) * PIXELS + dx) * 4;
          data[offset] = 0;
          data[offset + 1] = 0;
          data[offset + 2] = 0;
        }
      }
    });
  });
  return { data, side };
}

/** Dark modules drawn by a path of `M x y h n v1 h-n z` runs. */
function modulesOfPath(path: string, side: number): boolean[][] {
  const grid = Array.from({ length: side }, () => Array<boolean>(side).fill(false));
  for (const match of path.matchAll(/M(\d+) (\d+)h(\d+)v1h-\d+z/g)) {
    const [x, y, run] = [Number(match[1]), Number(match[2]), Number(match[3])];
    for (let index = 0; index < run; index += 1) {
      (grid[y] as boolean[])[x + index] = true;
    }
  }
  return grid;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("QR codes of share links", () => {
  it.each([
    "https://app.workshop.ge/c/mtsvane-ezo?src=table",
    "https://ig.me/m/mtsvane.ezo?ref=window",
    "https://wa.me/995599123456",
    "tel:+995322190019",
  ])("reads back as %s", (link) => {
    const matrix = encodeQr(link);
    const { data, side } = rasterize(matrix);

    expect(jsQR(data, side, side)?.data).toBe(link);
  });

  it("draws the same modules in the SVG path as in the grid, inside the quiet zone", () => {
    const matrix = encodeQr("https://app.workshop.ge/c/cafe");
    const grid = modulesOfPath(qrPath(matrix), qrSide(matrix));

    matrix.modules.forEach((row, y) => {
      row.forEach((isDark, x) => {
        expect(grid[y + QUIET_ZONE]?.[x + QUIET_ZONE]).toBe(isDark);
      });
    });
    expect(grid[0]?.some(Boolean)).toBe(false);
  });

  it("makes a standalone SVG file with an escaped title", () => {
    const svg = qrSvgDocument(encodeQr("https://x.example"), `Café "A" & <B>`);

    expect(svg).toMatch(/^<svg xmlns="http:\/\/www.w3.org\/2000\/svg" viewBox="0 0 \d+ \d+"/);
    expect(svg).toContain("<title>Café &quot;A&quot; &amp; &lt;B&gt;</title>");
    expect(escapeXml("it's")).toBe("it&#39;s");
  });

  it("draws the PNG on a canvas and saves files through a temporary link", async () => {
    const rects: number[][] = [];
    const context = { fillStyle: "", fillRect: (...args: number[]) => rects.push(args) };
    const canvas = {
      width: 0,
      height: 0,
      getContext: () => context,
      toBlob: (resolve: (blob: Blob | null) => void) => resolve(new Blob(["png"], { type: "image/png" })),
    };
    const anchor = { href: "", download: "", rel: "", click: vi.fn(), remove: vi.fn() };
    vi.stubGlobal("document", {
      createElement: (tag: string) => (tag === "canvas" ? canvas : anchor),
      body: { appendChild: vi.fn() },
    });
    vi.stubGlobal("window", { setTimeout: (callback: () => void) => callback() });
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:qr");
    const matrix = encodeQr("https://x.example");

    const blob = await qrPngBlob(matrix);
    saveBlob(blob as Blob, "chat-x.png");

    expect(canvas.width).toBe(qrSide(matrix) * 16);
    expect(rects[0]).toEqual([0, 0, canvas.width, canvas.width]);
    expect(rects.length).toBe(1 + matrix.modules.flat().filter(Boolean).length);
    expect(anchor).toMatchObject({ href: "blob:qr", download: "chat-x.png" });
    expect(anchor.click).toHaveBeenCalled();
    expect(revoke).toHaveBeenCalledWith("blob:qr");
  });

  it("draws nothing without a 2D context", () => {
    const canvas = { width: 0, height: 0, getContext: () => null } as unknown as HTMLCanvasElement;
    drawQr(encodeQr("x"), canvas, 2);
    expect(canvas.width).toBeGreaterThan(0);
  });
});
