/**
 * The import graph of the public site, read from the sources, for policy
 * tests about what its pages send to the browser (the dictionary share in
 * i18n/publicScope.test.ts, the code in app/_landing/publicBundle.test.ts).
 *
 * The public pages are what Next.js renders for /en, /ru/for/hotel,
 * /ka/terms…: the root layout and its special files, and everything under
 * app/[locale]. The modules that run in the browser are those marked
 * "use client" and whatever they import.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export const SRC = path.resolve(__dirname, "..");
const APP = path.join(SRC, "app");

function isFile(file: string): boolean {
  try {
    return statSync(file).isFile();
  } catch {
    return false;
  }
}

function publicEntries(): string[] {
  const special = ["layout.tsx", "error.tsx", "not-found.tsx", "global-error.tsx"]
    .map((name) => path.join(APP, name))
    .filter((file) => isFile(file));
  const walk = (folder: string): string[] =>
    readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
      const full = path.join(folder, entry.name);
      return entry.isDirectory() ? walk(full) : /^(page|layout|loading|error|not-found|template)\.tsx$/.test(entry.name) ? [full] : [];
    });
  return [...special, ...walk(path.join(APP, "[locale]"))];
}

function resolveImport(from: string, specifier: string): string | null {
  const base = specifier.startsWith("@/")
    ? path.join(SRC, specifier.slice(2))
    : specifier.startsWith(".")
      ? path.resolve(path.dirname(from), specifier)
      : null;
  if (base === null) {
    return null;
  }
  for (const suffix of ["", ".tsx", ".ts", "/index.tsx", "/index.ts"]) {
    if (isFile(base + suffix)) {
      return base + suffix;
    }
  }
  return null;
}

const STATIC_IMPORT = /^\s*(?:import|export)\s+(?!type\s)[^;]*?\sfrom\s+["']([^"']+)["']|^\s*import\s+["']([^"']+)["']/gm;
const DYNAMIC_IMPORT = /import\(\s*["']([^"']+)["']\s*\)/g;

/** What a module imports for its values (type-only imports leave no code): static, and with `import()`. */
export function importsOf(file: string): { static: string[]; dynamic: string[] } {
  const source = readFileSync(file, "utf8");
  return {
    static: [...source.matchAll(STATIC_IMPORT)].map((match) => match[1] ?? match[2] ?? ""),
    dynamic: [...source.matchAll(DYNAMIC_IMPORT)].map((match) => match[1] ?? ""),
  };
}

/** Whether a module runs in the browser by itself ("use client" on top). */
function isClientBoundary(source: string): boolean {
  return /^\s*["']use client["']/.test(source);
}

/**
 * The public pages' modules that run in the browser. With `lazy` false,
 * only those of the pages' first load: what is behind an `import()` (the
 * 3D scene, the toast list) is left out.
 */
export function publicClientModules({ lazy }: { lazy: boolean }): Set<string> {
  const clientModules = new Set<string>();
  const visited = new Map<string, boolean>();
  const visit = (file: string, inClient: boolean) => {
    const isClient = inClient || isClientBoundary(readFileSync(file, "utf8"));
    if (visited.get(file) === true || (visited.has(file) && !isClient)) {
      return;
    }
    visited.set(file, isClient);
    if (isClient) {
      clientModules.add(file);
    }
    const { static: staticImports, dynamic } = importsOf(file);
    for (const specifier of lazy ? [...staticImports, ...dynamic] : staticImports) {
      const target = resolveImport(file, specifier);
      if (target !== null && !target.includes(`${path.sep}i18n${path.sep}messages${path.sep}`)) {
        visit(target, isClient);
      }
    }
  };
  publicEntries().forEach((entry) => visit(entry, false));
  return clientModules;
}

/** A path relative to src/, for messages. */
export function fromSrc(file: string): string {
  return path.relative(SRC, file);
}
