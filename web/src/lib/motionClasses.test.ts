import { describe, expect, it } from "vitest";

import { parallaxClass, revealClasses, staggerClasses, tiltDepthClass } from "./motionClasses";
import { STAGGER } from "./motion";

describe("motion settings as classes", () => {
  it("adds nothing for the stylesheet's defaults", () => {
    expect(revealClasses(0, 0)).toBe("");
    expect(staggerClasses(0, STAGGER.landing)).toBe("");
  });

  it("sets the custom properties the CSS motion reads", () => {
    expect(revealClasses(1, 0.15)).toBe("[--reveal-depth:1] [--reveal-delay:0.15s]");
    expect(staggerClasses(0.15, 0.45)).toBe("[--stagger-delay:0.15s] [--stagger-step:0.45s]");
    expect(parallaxClass(-0.3)).toBe("[--parallax-shift:-36px]");
    expect(parallaxClass(0.6)).toBe("[--parallax-shift:72px]");
  });

  it("raises a tilting card's layer by its depth", () => {
    expect(tiltDepthClass(28)).toBe("translate-z-[28px]");
  });
});
