import { describe, expect, it } from "vitest";

import { CHAIN_VERDICT_TONES, chainVerdict } from "./auditChain";

describe("chainVerdict", () => {
  it("is unchecked until the first check ran", () => {
    expect(chainVerdict(undefined)).toBe("unchecked");
    expect(chainVerdict(null)).toBe("unchecked");
    expect(chainVerdict({ status: null })).toBe("unchecked");
  });

  it("names what the latest check found", () => {
    expect(chainVerdict({ status: "intact" })).toBe("intact");
    expect(chainVerdict({ status: "broken" })).toBe("broken");
  });

  it("marks only a broken chain as danger", () => {
    expect(CHAIN_VERDICT_TONES).toEqual({ unchecked: "neutral", intact: "success", broken: "danger" });
  });
});
