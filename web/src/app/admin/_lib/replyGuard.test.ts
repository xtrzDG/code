import { describe, expect, it } from "vitest";

import { guardFigures, isHeldBackOften, isProbed } from "./replyGuard";

const activity = (checked: number, rewritten: number, handedOff: number, flags = 0) => ({
  checked_replies: checked,
  rewritten_replies: rewritten,
  handed_off_replies: handedOff,
  injection_flags: flags,
});

describe("reply guard figures", () => {
  it("adds rewritten and handed-off replies and their share", () => {
    const figures = guardFigures(activity(30, 3, 2, 1));
    expect(figures.heldBack).toBe(5);
    expect(figures.heldBackShare).toBeCloseTo(5 / 30);
    expect(figures.injectionFlags).toBe(1);
  });

  it("has no share without checked replies", () => {
    expect(guardFigures(undefined)).toMatchObject({ checked: 0, heldBack: 0, heldBackShare: null });
  });

  it("follows the API's GUARD_SPIKE rule", () => {
    expect(isHeldBackOften(guardFigures(activity(24, 2, 2)))).toBe(false);
    expect(isHeldBackOften(guardFigures(activity(30, 3, 2)))).toBe(true);
    expect(isHeldBackOften(guardFigures(activity(31, 3, 2)))).toBe(false);
    expect(isProbed(guardFigures(activity(0, 0, 0, 9)))).toBe(false);
    expect(isProbed(guardFigures(activity(0, 0, 0, 10)))).toBe(true);
  });
});
