import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { fromSrc, importsOf, publicClientModules, SRC } from "@/test/publicModules";

/**
 * What a public page (/en, /ru/for/hotel, /ka/terms…) loads before anything
 * else: no 3D engine and no animation library. The landing hero's 3D scene
 * comes later, behind an `import()` (HeroVisual.tsx), only on capable wide
 * screens; the toasts' animated list comes with the first toast. The page
 * itself moves in CSS (src/components/siteMotion).
 */

const MOTION = /^(motion|framer-motion)(\/|$)/;
const THREE = /^(three|@react-three\/)/;
const SCENE_FOLDER = path.join("app", "_landing", "scene");
/** LazyMotion and MotionConfig only (no animation code): the root layout's provider for the cabinet. */
const MOTION_ALLOWED = new Set([path.join("components", "motion", "MotionProvider.tsx")]);

function packagesOf(file: string): string[] {
  return importsOf(file).static.filter((specifier) => !specifier.startsWith(".") && !specifier.startsWith("@/"));
}

function sourceFiles(folder: string): string[] {
  return readdirSync(folder).flatMap((name) => {
    const full = path.join(folder, name);
    return statSync(full).isDirectory() ? sourceFiles(full) : /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [full] : [];
  });
}

describe("the public pages' first load", () => {
  const firstLoad = publicClientModules({ lazy: false });
  const everything = publicClientModules({ lazy: true });

  it("is read from the real import graph", () => {
    expect(firstLoad.size).toBeGreaterThan(40);
    expect([...firstLoad].map(fromSrc)).toEqual(
      expect.arrayContaining([path.join("app", "_landing", "HeroVisual.tsx"), path.join("components", "ui", "ToastViewport.tsx")]),
    );
  });

  it("carries no 3D engine", () => {
    const offenders = [...firstLoad].filter((file) => packagesOf(file).some((name) => THREE.test(name))).map(fromSrc);
    expect(offenders).toEqual([]);
  });

  it("carries no animation library", () => {
    const offenders = [...firstLoad]
      .filter((file) => !MOTION_ALLOWED.has(fromSrc(file)) && packagesOf(file).some((name) => MOTION.test(name)))
      .map(fromSrc);
    expect(offenders).toEqual([]);
  });

  it("leaves the 3D scene and the animated toast list for later", () => {
    const later = [...everything].filter((file) => !firstLoad.has(file)).map(fromSrc);
    expect(later).toEqual(
      expect.arrayContaining([path.join(SCENE_FOLDER, "HeroScene.tsx"), path.join("components", "ui", "ToastList.tsx")]),
    );
  });
});

describe("the 3D engine", () => {
  it("is imported by the landing hero's scene alone, so no cabinet or niche page can carry it", () => {
    const importers = sourceFiles(SRC)
      .filter((file) => packagesOf(file).some((name) => THREE.test(name)))
      .map(fromSrc);
    expect(importers.length).toBeGreaterThan(0);
    expect(importers.filter((file) => !file.startsWith(SCENE_FOLDER + path.sep))).toEqual([]);
  });

  it("is reached only through the hero's import() of the scene", () => {
    const staticSceneImporters = sourceFiles(SRC)
      .filter((file) => !fromSrc(file).startsWith(SCENE_FOLDER + path.sep))
      .filter((file) => importsOf(file).static.some((specifier) => /(^|\/)scene\//.test(specifier)))
      .map(fromSrc);
    expect(staticSceneImporters).toEqual([]);
  });
});

describe("a link from the public site into the cabinet", () => {
  it("is a plain anchor, so the cabinet page loads whole and not inside the public site's layout", () => {
    // next/link (Link, ButtonLink) would navigate on the client, keeping the
    // public page's slim dictionary and leaving out the motion library.
    const clientLink = /<(Link|ButtonLink)\b[^>]*\bhref=\{(LOGIN_PATH|CREATE_PATH)\b/;
    const offenders = sourceFiles(path.join(SRC, "app", "_landing"))
      .filter((file) => clientLink.test(readFileSync(file, "utf8")))
      .map(fromSrc);
    expect(offenders).toEqual([]);
  });
});
