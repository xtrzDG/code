import { describe, expect, it } from "vitest";

import { PhoneChromeProvider, usePhoneChromeSnapshot } from "@/components/ui";
import { renderInLocale } from "@/test/render";

import { LiveStatus } from "./LiveStatus";

/** What the phone's top bar would show: the live dot and so the (i) beside the title. */
function BarProbe() {
  const { live } = usePhoneChromeSnapshot();
  return <output data-live={live ? String(live.updatedAt) : "none"} />;
}

const bar = (container: HTMLElement) => container.querySelector("output")?.dataset.live;

describe("the live status in the cabinet's shell", () => {
  it("is the top bar's dot", () => {
    const view = renderInLocale(
      <PhoneChromeProvider hasTopBar hasFabSlot>
        <LiveStatus updatedAt={1_000} />
        <BarProbe />
      </PhoneChromeProvider>,
    );
    expect(bar(view.container)).toBe("1000");
  });

  it("stays registered while the bar yields to an open conversation, so the bar comes back whole", () => {
    // The inbox list's status, its layout kept while a conversation covers the bar (hasTopBar false).
    const view = renderInLocale(
      <PhoneChromeProvider hasTopBar={false} hasFabSlot={false}>
        <LiveStatus updatedAt={1_000} />
        <BarProbe />
      </PhoneChromeProvider>,
    );
    expect(bar(view.container)).toBe("1000");
  });

  it("registers nothing outside the shell", () => {
    const view = renderInLocale(
      <>
        <LiveStatus updatedAt={1_000} />
        <BarProbe />
      </>,
    );
    expect(bar(view.container)).toBe("none");
  });
});
