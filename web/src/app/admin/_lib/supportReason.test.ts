import { describe, expect, it } from "vitest";

import { SUPPORT_REASON_MAX, cleanSupportReason, isSupportReasonValid } from "./supportReason";

describe("support reason", () => {
  it("needs a real sentence the owner can read", () => {
    expect(isSupportReasonValid("")).toBe(false);
    expect(isSupportReasonValid("   check   ")).toBe(false);
    expect(isSupportReasonValid("Owner asked why bookings stopped")).toBe(true);
    expect(isSupportReasonValid("x".repeat(SUPPORT_REASON_MAX + 1))).toBe(false);
  });

  it("sends the reason without blanks around it", () => {
    expect(cleanSupportReason("  Help with the hours \n")).toBe("Help with the hours");
  });
});
