import { describe, expect, it } from "vitest";

import { isConfirmationTyped } from "./confirmation";

describe("isConfirmationTyped", () => {
  it("ignores case and surrounding spaces", () => {
    expect(isConfirmationTyped(" delete ", "DELETE")).toBe(true);
    expect(isConfirmationTyped("Нино", "нино")).toBe(true);
    expect(isConfirmationTyped("delet", "DELETE")).toBe(false);
  });

  it("never unlocks an empty expectation", () => {
    expect(isConfirmationTyped("", "  ")).toBe(false);
  });
});
