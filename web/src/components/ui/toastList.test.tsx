import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { useToastList as UseToastList } from "./toastList";

/** Shows whether the toast list has arrived for a viewport that needs it (or not yet). */
function probeFor(useToastList: typeof UseToastList) {
  return function Probe({ isNeeded }: { isNeeded: boolean }) {
    const renderList = useToastList(isNeeded);
    return <p>{renderList ? "list" : "no list"}</p>;
  };
}

describe("the toast list's own chunk", () => {
  it("is fetched when a toast first has to be shown, and is there at once for every viewport after", async () => {
    // A fresh copy of the loader: the test setup has already loaded the list for the other tests.
    vi.resetModules();
    const { useToastList } = await import("./toastList");
    const Probe = probeFor(useToastList);

    const first = render(<Probe isNeeded={false} />);
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(screen.getByText("no list")).toBeTruthy();

    first.rerender(<Probe isNeeded />);
    expect(await screen.findByText("list")).toBeTruthy();
    first.unmount();

    render(<Probe isNeeded={false} />);
    expect(screen.getByText("list")).toBeTruthy();
  });
});
