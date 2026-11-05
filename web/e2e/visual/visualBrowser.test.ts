/**
 * scripts/visual-browser.mjs: the visual tests' browser is Playwright's own
 * image for the runner's exact version, pinned by digest, serving this
 * checkout's Playwright; the run compares unless asked to update.
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { dockerRunArguments, playwrightArguments, publishedPort, VISUAL_BROWSER_IMAGE } from "../../scripts/visual-browser.mjs";

const PACKAGE = JSON.parse(readFileSync(path.join(__dirname, "..", "..", "package.json"), "utf8")) as {
  devDependencies: Record<string, string>;
};

describe("the visual tests' browser", () => {
  it("is the image of the runner's Playwright version, pinned by digest", () => {
    const version = PACKAGE.devDependencies["@playwright/test"];
    expect(VISUAL_BROWSER_IMAGE).toMatch(/^mcr\.microsoft\.com\/playwright:v[\d.]+-noble@sha256:[0-9a-f]{64}$/);
    expect(VISUAL_BROWSER_IMAGE.startsWith(`mcr.microsoft.com/playwright:v${version}-noble@`), "update the image with @playwright/test").toBe(
      true,
    );
  });

  it("serves this checkout's Playwright, read-only, on a loopback port only", () => {
    const args = dockerRunArguments({ name: "visual-browser-1", nodeModules: "/repo/web/node_modules" });
    expect(args.slice(0, 4)).toEqual(["run", "--detach", "--rm", "--init"]);
    expect(args).toContain("127.0.0.1::3000");
    expect(args).toContain("/repo/web/node_modules:/visual/node_modules:ro");
    expect(args.slice(args.indexOf(VISUAL_BROWSER_IMAGE) + 1)).toEqual([
      "node",
      "/visual/node_modules/playwright/cli.js",
      "run-server",
      "--port",
      "3000",
      "--host",
      "0.0.0.0",
    ]);
  });

  it("compares by default and writes only the changed baselines when asked", () => {
    expect(playwrightArguments(false, ["new-business"])).toEqual([
      "playwright",
      "test",
      "--config",
      "e2e/playwright.config.ts",
      "--project",
      "visual",
      "--update-snapshots=none",
      "new-business",
    ]);
    expect(playwrightArguments(true, [])).toContain("--update-snapshots=changed");
  });

  it("reads the port Docker published", () => {
    expect(publishedPort("127.0.0.1:49153\n")).toBe(49153);
    expect(() => publishedPort("")).toThrow(/no port/);
  });
});
