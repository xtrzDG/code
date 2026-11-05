import { render } from "@testing-library/react";
import { useLayoutEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChromeStore } from "@/lib/phoneChrome";

import { PhoneChromeProvider, usePhoneDescription, usePhoneLive } from "./PhoneChrome";

/** A page that puts its live dot and its (i) in the phone's top bar. */
function Page() {
  usePhoneLive(1, { updatedAt: 1_000, isFetching: false });
  usePhoneDescription(1, { title: "Inbox", text: "Every conversation" });
  return null;
}

/**
 * Runs in the same commit as the page, after its layout effects (siblings'
 * layout effects run in order) and before the browser paints: what the top
 * bar can know for the page's first frame.
 */
function BeforePaint({ onLayout }: { onLayout: () => void }) {
  useLayoutEffect(() => {
    onLayout();
  });
  return null;
}

describe("the phone chrome a page registers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("is there before the browser paints the page, so the top bar's buttons never move after it shows", () => {
    const set = vi.spyOn(ChromeStore.prototype, "set");
    let registeredBeforePaint = -1;
    render(
      <PhoneChromeProvider hasTopBar hasFabSlot>
        <Page />
        <BeforePaint
          onLayout={() => {
            registeredBeforePaint = set.mock.calls.length;
          }}
        />
      </PhoneChromeProvider>,
    );
    // The live dot and the (i): both registered in the layout phase, not after the paint.
    expect(registeredBeforePaint).toBe(2);
  });
});
