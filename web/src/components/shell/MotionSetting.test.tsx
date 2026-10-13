import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MotionPreferenceProvider, useMotionPreference } from "@/components/motion/MotionPreference";
import { renderInLocale, textsIn } from "@/test/render";

import { MotionSetting } from "./MotionSetting";

/** The checkbox by its label (its accessible name goes on with the hint). */
function motionBox(locale: "en" | "ru" | "ka" | "he" | "de" = "en"): HTMLInputElement {
  const label = textsIn(locale).t("account.motion");
  return screen.getByRole<HTMLInputElement>("checkbox", { name: (name) => name.startsWith(label) });
}

const calmText = () => screen.getByLabelText("calm").textContent;

function Calm() {
  const { isCalm } = useMotionPreference();
  return <output aria-label="calm">{String(isCalm)}</output>;
}

/** A device whose "reduce motion" setting the test flips, as matchMedia reports it. */
function stubDevice(reduces: boolean) {
  const listeners = new Set<() => void>();
  const state = { reduces };
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        get matches() {
          return query.includes("reduce") && state.reduces;
        },
        media: query,
        addEventListener: (_type: string, listener: () => void) => listeners.add(listener),
        removeEventListener: (_type: string, listener: () => void) => listeners.delete(listener),
      }) as unknown as MediaQueryList,
  );
  return (next: boolean) => {
    state.reduces = next;
    act(() => listeners.forEach((listener) => listener()));
  };
}

describe("Reduce motion in the account menu", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-motion");
    document.cookie = "aw_motion=; max-age=0; path=/";
  });

  it("calms the page at once and keeps the choice in the cookie", async () => {
    stubDevice(false);
    renderInLocale(
      <MotionPreferenceProvider initialPreference="system">
        <MotionSetting />
        <Calm />
      </MotionPreferenceProvider>,
    );
    const box = motionBox();
    expect(box.checked).toBe(false);
    expect(calmText()).toBe("false");

    await userEvent.click(box);
    expect(box.checked).toBe(true);
    expect(document.documentElement.getAttribute("data-motion")).toBe("reduce");
    expect(document.cookie).toContain("aw_motion=reduce");
    expect(calmText()).toBe("true");

    await userEvent.click(box);
    expect(document.documentElement.hasAttribute("data-motion")).toBe(false);
    expect(document.cookie).toContain("aw_motion=system");
    expect(calmText()).toBe("false");
  });

  it("stays calm while the device asks for less motion, whatever the choice", () => {
    const setDevice = stubDevice(false);
    renderInLocale(
      <MotionPreferenceProvider initialPreference="system">
        <Calm />
      </MotionPreferenceProvider>,
      { locale: "ka" },
    );
    expect(calmText()).toBe("false");
    setDevice(true);
    expect(calmText()).toBe("true");
    setDevice(false);
    expect(calmText()).toBe("false");
  });

  it("is labelled in every cabinet language", () => {
    stubDevice(false);
    for (const locale of ["ru", "ka", "he", "de"] as const) {
      const view = renderInLocale(
        <MotionPreferenceProvider initialPreference="reduce">
          <MotionSetting />
        </MotionPreferenceProvider>,
        { locale },
      );
      expect(motionBox(locale).checked).toBe(true);
      view.unmount();
    }
  });
});
