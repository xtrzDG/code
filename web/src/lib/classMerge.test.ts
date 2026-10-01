import { describe, expect, it } from "vitest";

import { classGroup, mergeClassOverrides } from "./classMerge";

describe("classGroup", () => {
  it.each([
    ["w-full", "w"],
    ["w-32", "w"],
    ["min-w-0", "min-w"],
    ["max-w-sm", "max-w"],
    ["h-10", "h"],
    ["px-3", "px"],
    ["text-sm", "font-size"],
    ["text-[13px]", "font-size"],
    ["text-ink-muted", "text-colour"],
    ["text-danger", "text-colour"],
    ["bg-accent-solid", "background-colour"],
    ["bg-danger-soft", "background-colour"],
    ["border-line-strong", "border-colour"],
    ["rounded-lg", "rounded"],
    ["rounded", "rounded"],
  ])("%s belongs to %s", (utility, group) => {
    expect(classGroup(utility)).toBe(group);
  });

  it.each(["text-center", "text-nowrap", "border", "border-2", "border-b", "border-dashed", "bg-cover", "rounded-t-lg", "flex", "gap-2", "shadow-sm"])(
    "%s is left alone",
    (utility) => {
      expect(classGroup(utility)).toBeNull();
    },
  );
});

describe("mergeClassOverrides", () => {
  it("keeps the base classes without overrides", () => {
    expect(mergeClassOverrides("w-full h-10", undefined)).toBe("w-full h-10");
    expect(mergeClassOverrides("w-full h-10", "")).toBe("w-full h-10");
  });

  it("replaces a width", () => {
    expect(mergeClassOverrides("block w-full h-10 px-3", "w-32")).toBe("block h-10 px-3 w-32");
  });

  it("replaces colours per variant and keeps the others", () => {
    const base = "text-ink-muted hover:bg-surface-muted hover:text-ink focus-visible:outline-focus";
    expect(mergeClassOverrides(base, "text-danger hover:bg-danger-soft hover:text-danger")).toBe(
      "focus-visible:outline-focus text-danger hover:bg-danger-soft hover:text-danger",
    );
  });

  it("treats important classes like plain ones", () => {
    expect(mergeClassOverrides("text-ink hover:text-ink", "text-danger!")).toBe("hover:text-ink text-danger!");
  });

  it("does not mix font sizes with colours or responsive variants with plain ones", () => {
    expect(mergeClassOverrides("text-sm text-ink sm:w-auto", "text-base w-full")).toBe("text-ink sm:w-auto text-base w-full");
  });

  it("keeps border widths when the colour changes", () => {
    expect(mergeClassOverrides("border border-line-strong", "border-danger")).toBe("border border-danger");
  });
});
