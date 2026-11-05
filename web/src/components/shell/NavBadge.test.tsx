import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MotionPreferenceProvider } from "@/components/motion/MotionPreference";
import { renderInLocale, textsIn } from "@/test/render";

import { NavBadge } from "./NavBadge";

const badge = (container: HTMLElement) => container.querySelector<HTMLElement>("[data-badge-count]");

describe("the navigation badge", () => {
  const animate = vi.fn();

  beforeEach(() => {
    animate.mockClear();
    // jsdom has no Web Animations: the beat is observed through this stand-in.
    Object.defineProperty(HTMLElement.prototype, "animate", { value: animate, configurable: true, writable: true });
  });

  afterEach(() => {
    delete (HTMLElement.prototype as Partial<HTMLElement>).animate;
  });

  it("shows the number, tells screen readers what waits, and nothing for zero", () => {
    const view = renderInLocale(<NavBadge count={3} />);
    expect(badge(view.container)?.dataset.badgeCount).toBe("3");
    expect(badge(view.container)?.textContent).toBe(`3, ${textsIn("en").tp("navigation.waiting", 3)}`);
    view.rerender(<NavBadge count={0} />);
    expect(badge(view.container)).toBeNull();
  });

  it("beats once when the number grows, not when it falls or first appears", () => {
    const view = renderInLocale(<NavBadge count={2} />);
    expect(animate).not.toHaveBeenCalled();
    view.rerender(<NavBadge count={4} />);
    expect(animate).toHaveBeenCalledTimes(1);
    expect(badge(view.container)?.textContent?.startsWith("4")).toBe(true);
    view.rerender(<NavBadge count={1} />);
    expect(animate).toHaveBeenCalledTimes(1);
  });

  it("keeps still when the person asked for calm", () => {
    const view = renderInLocale(
      <MotionPreferenceProvider initialPreference="reduce">
        <NavBadge count={2} />
      </MotionPreferenceProvider>,
    );
    view.rerender(
      <MotionPreferenceProvider initialPreference="reduce">
        <NavBadge count={7} />
      </MotionPreferenceProvider>,
    );
    expect(animate).not.toHaveBeenCalled();
    expect(badge(view.container)?.textContent?.startsWith("7")).toBe(true);
  });
});
