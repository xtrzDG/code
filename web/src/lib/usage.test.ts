import { describe, expect, it } from "vitest";

import { isUsageWarned, USAGE_WARNING_PERCENT, usageLevel } from "./usage";

describe("package usage", () => {
  it("warns from 80 % and flags overage from 100 %", () => {
    expect(USAGE_WARNING_PERCENT).toBe(80);
    expect(usageLevel(0)).toBe("ok");
    expect(usageLevel(79)).toBe("ok");
    expect(usageLevel(80)).toBe("warning");
    expect(usageLevel(99)).toBe("warning");
    expect(usageLevel(100)).toBe("exceeded");
    expect(usageLevel(250)).toBe("exceeded");
  });

  it("has no level for a package without the unit", () => {
    expect(usageLevel(null)).toBe("none");
    expect(usageLevel(undefined)).toBe("none");
    expect(usageLevel(Number.NaN)).toBe("none");
  });

  it("asks the owner to act only on a warning or overage", () => {
    expect([usageLevel(null), usageLevel(10), usageLevel(85), usageLevel(120)].map(isUsageWarned)).toEqual([false, false, true, true]);
  });
});
