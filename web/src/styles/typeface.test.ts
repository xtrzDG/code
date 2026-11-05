import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * The self-hosted typeface (typeface.css, public/fonts/): small files, its
 * licence beside them, one file per code point, Latin last in the stack so
 * its size-adjusted fallback never takes another script's letters, and
 * the faces named only under the cabinet's class.
 */

const WEB = fileURLToPath(new URL("../..", import.meta.url));
const FONTS = path.join(WEB, "public", "fonts");
const MAX_SUBSET_BYTES = 60 * 1024;
const typeface = readFileSync(path.join(WEB, "src", "styles", "typeface.css"), "utf8");
const globals = readFileSync(path.join(WEB, "src", "app", "globals.css"), "utf8");

/** The brand class's variables: each one's name and the family it names first. */
const brandClass = /\.brand-typeface \{([^}]*)\}/.exec(typeface)?.[1] ?? "";
const variables = [...brandClass.matchAll(/(--font-brand-[a-z-]+): "([^"]+)"/g)].map((match) => ({
  variable: match[1] ?? "",
  family: match[2] ?? "",
}));

/** Each @font-face that loads a file: its family, file and unicode-range, and the variable naming it. */
const faces = [...typeface.matchAll(/@font-face \{([^}]*)\}/g)]
  .map((match) => match[1] ?? "")
  .filter((body) => body.includes("url("))
  .map((body) => {
    const family = /font-family: "([^"]+)"/.exec(body)?.[1] ?? "";
    return {
      body,
      family,
      variable: variables.find((entry) => entry.family === family)?.variable ?? "",
      file: /url\("\.\.\/\.\.\/public\/fonts\/([^"]+)"\)/.exec(body)?.[1] ?? "",
      ranges: (/unicode-range:([^;]+);/.exec(body)?.[1] ?? "").split(",").map((range) => {
        const [start = "", end = start] = range.trim().replace(/U\+/g, "").split("-");
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
      expect(face.body, face.file).toContain("font-display: optional;");
    }
    // Latin alone brings the size-adjusted fallback; it stands in for every script.
    expect(variables.map((entry) => entry.variable === "--font-brand-latin")).toEqual([true, false, false, false, false]);
    expect(brandClass).toContain('--font-brand-latin: "Brand Latin", "Brand Latin Fallback";');
    expect(typeface).toMatch(/font-family: "Brand Latin Fallback";\s*src: local\("Arial"\);\s*ascent-override/);
    const stack = /--font-sans:([^;]+);/.exec(globals)?.[1] ?? "";
    const order = faces.map((face) => stack.indexOf(`var(${face.variable},`));
    expect(order.every((position) => position >= 0)).toBe(true);
    expect(Math.max(...order)).toBe(order[0]);
  });

  it("names its families only under the cabinet's class, so the public site keeps the system's fonts", () => {
    // Outside the @font-face rules the families appear in that one rule, and the stylesheet that
    // declares them is the one every page loads anyway: no extra request on the public site.
    const outsideFaces = typeface.replace(/\/\*[\s\S]*?\*\//g, "").replace(/@font-face \{[^}]*\}/g, "").trim();
    expect(outsideFaces.match(/"Brand [A-Za-z ]+"/g)?.length).toBe(variables.length + 1);
    expect(outsideFaces.startsWith(".brand-typeface {")).toBe(true);
    expect(globals).toContain('@import "../styles/typeface.css";');
    expect(globals).not.toMatch(/--font-brand-[a-z-]+:/);
  });

  it("keeps other scripts' files out of the language picker, whose options name every language", () => {
    // A closed select's options are shaped with its font: with --font-sans an English cabinet page
    // fetched the Georgian, Cyrillic and Hebrew files ahead of its first paint.
    const stack = /--font-language-names:([^;]+);/.exec(globals)?.[1] ?? "";
    expect([...stack.matchAll(/var\((--[a-z-]+),/g)].map((match) => match[1])).toEqual(["--font-page-script", "--font-brand-latin"]);
    const pageScripts = [...globals.matchAll(/:root:lang\(([a-z]+)\) \{\s*--font-page-script: var\((--[a-z-]+),/g)];
    expect(Object.fromEntries(pageScripts.map((match) => [match[1], match[2]]))).toEqual({
      ru: "--font-brand-cyrillic",
      ka: "--font-brand-georgian",
      he: "--font-brand-hebrew",
    });
    const switcher = readFileSync(path.join(WEB, "src", "components", "LanguageSwitcher.tsx"), "utf8");
    expect(/<select[\s\S]*?className=\{cn\(\s*"[^"]*\bfont-language-names\b/.test(switcher)).toBe(true);
  });
});
