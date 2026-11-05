import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MotionPreferenceProvider } from "./MotionPreference";
import { morphName, SharedMorph } from "./SharedMorph";

/** Gives the test document the View Transitions API (jsdom has none), or takes it away. */
function setViewTransitions(isSupported: boolean) {
  if (isSupported) {
    Object.defineProperty(document, "startViewTransition", { value: () => undefined, configurable: true, writable: true });
  } else {
    Reflect.deleteProperty(document, "startViewTransition");
  }
}

describe("a shared-element morph", () => {
  afterEach(() => {
    setViewTransitions(false);
  });

  it("names one part of one record as a CSS identifier", () => {
    expect(morphName("conversation-name", "c_01H8")).toBe("aw-conversation-name-c_01H8");
    expect(morphName("conversation-avatar", "a b/c:1.2")).toBe("aw-conversation-avatar-a_b_c_1_2");
  });

  it("shows its content where the browser cannot morph", () => {
    render(
      <SharedMorph name="aw-conversation-name-1">
        <span>Nino</span>
      </SharedMorph>,
    );
    expect(screen.getByText("Nino")).toBeTruthy();
  });

  it("shows its content where it can, calm or not, active or not", () => {
    setViewTransitions(true);
    const view = render(
      <SharedMorph name="aw-conversation-name-1">
        <span>Nino</span>
      </SharedMorph>,
    );
    expect(screen.getByText("Nino")).toBeTruthy();
    view.rerender(
      <SharedMorph name="aw-conversation-name-1" active={false}>
        <span>Nino</span>
      </SharedMorph>,
    );
    expect(screen.getByText("Nino")).toBeTruthy();
    view.rerender(
      <MotionPreferenceProvider initialPreference="reduce">
        <SharedMorph name="aw-conversation-name-1">
          <span>Nino</span>
        </SharedMorph>
      </MotionPreferenceProvider>,
    );
    expect(screen.getByText("Nino")).toBeTruthy();
  });
});
