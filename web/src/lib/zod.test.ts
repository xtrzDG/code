import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { z } from "./zod";

describe("the cabinet's zod", () => {
  it("never compiles schemas with new Function", () => {
    expect(z.config().jitless).toBe(true);
  });

  it("is kept with its configuration by the bundler, although it only passes zod on", () => {
    // package.json marks the project's modules free of side effects, so a
    // bundler may skip a module that only re-exports and go to zod directly:
    // the configuration call would then never run in the browser.
    const manifest = JSON.parse(readFileSync(join(process.cwd(), "package.json"), "utf8")) as {
      sideEffects: string[];
    };
    expect(manifest.sideEffects).toContain("./src/lib/zod.ts");
  });
});
