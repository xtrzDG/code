/**
 * The `visual` project of playwright.config.ts (README "Visual tests and the
 * review gate"): screenshots of every page compared with the baselines in
 * e2e/visual/__screenshots__, and the review gate's checks of each page.
 *
 * It runs only with E2E_VISUAL=1 (`npm run e2e:visual`, which sets it) and
 * never in the suite's shards: its spec files live in e2e/visual/, which
 * the shard plan (support/shards.ts reads e2e/ only) and the other projects
 * leave out. The browser is the one of Playwright's image, reached at
 * VISUAL_BROWSER_WS (scripts/visual-browser.mjs starts it): the host's
 * Chromium renders other pixels than CI's, so the project refuses to run
 * without it.
 */

import path from "node:path";

import { devices, type Project } from "@playwright/test";

import { WEB_DIRECTORY } from "../support/env";
import { DESKTOP, VISUAL_ZONE } from "./clock";

/** `next` of a visual run: its `Date` stands still at the browser's moment (server-clock.mjs). */
export const VISUAL_NEXT = "node --import ./e2e/visual/server-clock.mjs node_modules/next/dist/bin/next";

/** Paths of the visual project's files, for the other projects' testIgnore. */
export const VISUAL_FILES = /[\\/]e2e[\\/]visual[\\/]/;

/** The first project's spec: the demo owner's sign-in and the platform admin's pages. */
const PLATFORM_SPEC = /platform\.spec\.ts$/;

/** Workers of a visual run: the pages are read-only views of the demo data, taken side by side. */
export const VISUAL_WORKERS = 3;

/**
 * The visual projects: `visual-platform` first (one worker: the demo owner
 * signs in once, the admin's pages see the platform before the other tests
 * add to it), then `visual`, every test on its own (`fullyParallel`).
 */
export function visualProjects(wsEndpoint: string | undefined): Project[] {
  if (!wsEndpoint) {
    throw new Error(
      "The visual tests run in the browser of Playwright's image: `npm run e2e:visual` " +
        "(scripts/visual-browser.mjs starts it and sets VISUAL_BROWSER_WS).",
    );
  }
  const shared: Project = {
    // A picture that differs on a second try is a finding, not bad luck; and
    // the new business of new-business.spec.ts exists once per run.
    retries: 0,
    testDir: path.join(WEB_DIRECTORY, "e2e", "visual"),
    // One baseline per screen, the same on every machine (the browser is the image's).
    snapshotPathTemplate: "{testDir}/__screenshots__/{testFileName}/{arg}{ext}",
    expect: { toHaveScreenshot: { animations: "disabled", caret: "hide", scale: "css" } },
    use: {
      ...devices["Desktop Chrome"],
      viewport: DESKTOP.viewport,
      deviceScaleFactor: 1,
      // The demo restaurant's zone: the reader sees the business's own times.
      timezoneId: VISUAL_ZONE,
      // The cabinet listens on this machine's loopback; the runner carries the browser's requests there.
      connectOptions: { wsEndpoint, exposeNetwork: "<loopback>" },
    },
  };
  return [
    { ...shared, name: "visual-platform", testMatch: PLATFORM_SPEC, workers: 1 },
    {
      ...shared,
      name: "visual",
      testMatch: /\.spec\.ts$/,
      testIgnore: PLATFORM_SPEC,
      dependencies: ["visual-platform"],
      fullyParallel: true,
    },
  ];
}
