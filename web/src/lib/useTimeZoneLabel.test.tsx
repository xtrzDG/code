import { act, render, screen } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useTimeZoneLabel } from "./useTimeZoneLabel";

function Note() {
  const zoneLabel = useTimeZoneLabel("en");
  return <p data-testid="note">Times in {zoneLabel("Europe/Berlin")}</p>;
}

/** Berlin leaves summer time on 25 October 2026: UTC+2 the day before, UTC+1 after. */
const SUMMER = new Date("2026-10-24T08:30:00Z");
const WINTER = new Date("2026-10-25T09:30:00Z");

afterEach(() => {
  vi.useRealTimers();
  document.body.innerHTML = "";
});

describe("useTimeZoneLabel", () => {
  it("names the city alone in the server's HTML", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(SUMMER);

    const container = document.createElement("div");
    container.innerHTML = renderToString(<Note />);

    expect(container.textContent).toBe("Times in Berlin");
  });

  it("hydrates across a change of the clocks and then names the browser's offset", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(SUMMER);
    const container = document.createElement("div");
    container.innerHTML = renderToString(<Note />);
    document.body.append(container);
    // The browser's clock is a day later, past the change (as in an e2e test's fixed clock).
    vi.setSystemTime(WINTER);
    const recoverable = vi.fn();

    await act(async () => {
      hydrateRoot(container, <Note />, { onRecoverableError: recoverable });
    });

    expect(recoverable).not.toHaveBeenCalled();
    expect(container.textContent).toBe("Times in Berlin (UTC+1)");
  });

  it("names the offset at once in a component first rendered in the browser", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(SUMMER);

    render(<Note />);

    expect(screen.getByTestId("note").textContent).toBe("Times in Berlin (UTC+2)");
  });
});
