/** support/apiClock.ts reads how far the visual tests' API runs ahead from its log. */

import { describe, expect, it } from "vitest";

import { clockOffsetMs } from "./apiClock";

describe("the API's clock offset", () => {
  it("is the started clock's lead over the machine, from its first log line", () => {
    const log = [
      "INFO uvicorn.error: Started server process",
      "WARNING scripts.visual_api: Visual clock: 1791963000.000000000 s at the machine's 1793030000.123456789 s",
      "WARNING scripts.visual_api: Visual clock: 0.000000001 s at the machine's 0.000000002 s",
    ].join("\n");
    expect(clockOffsetMs(log)).toBe(-1_067_000_123);
  });

  it("is nothing for the suite's own API, whose clock is the machine's", () => {
    expect(clockOffsetMs("INFO uvicorn.error: Started server process\n")).toBe(0);
  });
});
