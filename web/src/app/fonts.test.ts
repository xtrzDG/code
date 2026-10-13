import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The self-hosted typeface (fonts.ts, public/fonts/): small files, its
 * licence beside them, one file per code point, and Latin last in the
 * stack so its size-adjusted fallback never takes another script's letters.
 */

const WEB = fileURLToPath(new URL("../..", import.meta.url));
const FONTS = path.join(WEB, "public", "fonts");
const MAX_SUBSET_BYTES = 60 * 1024;
const fontsSource = readFileSync(path.join(WEB, "src", "app", "fonts.ts"), "utf8");

/** Each localFont call: its file, CSS variable and unicode-range, in order. */
const faces = [...fontsSource.matchAll(/localFont\(\{([\s\S]*?)\n\}\);/g)].map((match) => {
  const body = match[1] ?? "";
  return {
    body,
    file: /src: "\.\.\/\.\.\/public\/fonts\/([^"]+)"/.exec(body)?.[1] ?? "",
    variable: /variable: "(--[a-z-]+)"/.exec(body)?.[1] ?? "",
    ranges: (/"(U\+[0-9A-F+,U-]+)"/.exec(body)?.[1] ?? "").split(",").map((range) => {
      const [start = "", end = start] = range.replace(/U\+/g, "").split("-");
      return [Number.parseInt(start, 16), Number.parseInt(end, 16)] as const;
    }),
  };
});

describe("the self-hosted typeface", () => {
  it("loads a file per script: Latin, extended Latin, Cyrillic, Georgian and Hebrew", () => {
    expect(faces.map((face) => face.variable)).toEqual([
      "--font-brand-latin",
      "--font-brand-latin-ext",
      "--font-brand-cyrillic",
      "--font-brand-georgian",
      "--font-brand-hebrew",
    ]);
  });

  it("keeps every subset a variable woff2 of at most 60 KB, and nothing else in the folder", () => {
    const files = readdirSync(FONTS).filter((name) => name.endsWith(".woff2"));
    expect(files.sort()).toEqual(faces.map((face) => face.file).sort());
    for (const name of files) {
      const body = readFileSync(path.join(FONTS, name));
      expect(body.subarray(0, 4).toString("latin1"), name).toBe("wOF2");
      expect(statSync(path.join(FONTS, name)).size, name).toBeLessThanOrEqual(MAX_SUBSET_BYTES);
    }
  });

  it("ships the SIL Open Font License beside the files", () => {
    const licence = readFileSync(path.join(FONTS, "OFL.txt"), "utf8");
    expect(licence).toContain("SIL OPEN FONT LICENSE Version 1.1");
    expect(licence).toContain("The Noto Project Authors");
  });

  it("gives each code point to one file only", () => {
    const all = faces.flatMap((face) => face.ranges.map(([start, end]) => ({ file: face.file, start, end })));
    expect(all.every(({ start, end }) => Number.isFinite(start) && start <= end)).toBe(true);
    for (const [index, range] of all.entries()) {
      for (const other of all.slice(index + 1)) {
        const overlaps = range.start <= other.end && other.start <= range.end;
        expect(overlaps, `${range.file} and ${other.file}`).toBe(false);
      }
    }
  });

  it("never shifts the layout: no swap after the first paint, and Latin with its fallback last", () => {
    for (const face of faces) {
      expect(face.body, face.file).toContain('display: "optional"');
    }
    // Latin alone brings the size-adjusted fallback; it stands in for every script.
    expect(faces.map((face) => /adjustFontFallback: ("Arial"|false)/.exec(face.body)?.[1])).toEqual(['"Arial"', "false", "false", "false", "false"]);
    const css = readFileSync(path.join(WEB, "src", "app", "globals.css"), "utf8");
    const stack = /--font-sans:([^;]+);/.exec(css)?.[1] ?? "";
    const order = faces.map((face) => stack.indexOf(`var(${face.variable},`));
    expect(order.every((position) => position >= 0)).toBe(true);
    expect(Math.max(...order)).toBe(order[0]);
  });
});
