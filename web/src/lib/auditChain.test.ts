import { describe, expect, it } from "vitest";

import { CHAIN_VERDICT_TONES, chainVerdict } from "./auditChain";

describe("chainVerdict", () => {
  it("is unchecked until the first check ran", () => {
    expect(chainVerdict(undefined)).toBe("unchecked");
    expect(chainVerdict(null)).toBe("unchecked");
    expect(chainVerdict({ status: null })).toBe("unchecked");
  });

  it("names what the latest check found", () => {
    expect(chainVerdict({ status: "intact", verified_through_position: 12 })).toBe("intact");
    expect(chainVerdict({ status: "broken" })).toBe("broken");
  });

  it("never calls a log without a sealed entry intact", () => {
    expect(chainVerdict({ status: "intact" })).toBe("unsealed");
    expect(chainVerdict({ status: "intact", verified_through_position: null })).toBe("unsealed");
  });

  it("marks only a broken chain as danger and only a sealed one as intact", () => {
    expect(CHAIN_VERDICT_TONES).toEqual({ unchecked: "neutral", unsealed: "neutral", intact: "success", broken: "danger" });
  });
});
