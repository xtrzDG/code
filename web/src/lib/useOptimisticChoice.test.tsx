import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { useOptimisticChoice } from "./useOptimisticChoice";

type Period = "7d" | "30d";

/** A choice whose page takes the new value only through `onChange` (as the URL does). */
function Choice({ initial, onChange }: { initial: Period; onChange: (period: Period) => void }) {
  const [value, setValue] = useState<Period>(initial);
  const [shown, choose] = useOptimisticChoice(value, (next: Period) => {
    onChange(next);
    setValue(next);
  });
  return (
    <div>
      <output data-testid="page">{value}</output>
      {(["7d", "30d"] as const).map((period) => (
        <button key={period} type="button" aria-pressed={shown === period} onClick={() => choose(period)}>
          {period}
        </button>
      ))}
    </div>
  );
}

describe("useOptimisticChoice", () => {
  it("shows the choice at once and changes the page only after the next paint", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Choice initial="7d" onChange={onChange} />);

    // A frame callback that never runs: the page must not change during the tap.
    const frame = vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 1);
    await user.click(screen.getByRole("button", { name: "30d" }));
    expect(screen.getByRole("button", { name: "30d" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "7d" }).getAttribute("aria-pressed")).toBe("false");
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByTestId("page").textContent).toBe("7d");

    // The frame paints: the page follows, and the shown choice is the page's own again.
    const paint = frame.mock.calls[0]?.[0];
    frame.mockRestore();
    expect(paint).toBeDefined();
    act(() => paint?.(performance.now()));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith("30d"));
    // The page's own redraw is a transition: it lands a moment later.
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("30d"));
    expect(screen.getByRole("button", { name: "30d" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("does nothing for the choice already shown", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Choice initial="7d" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "7d" }));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("drops a pending change when the control goes away before the paint", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { unmount } = render(<Choice initial="7d" onChange={onChange} />);

    const frame = vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 7);
    const cancel = vi.spyOn(window, "cancelAnimationFrame");
    await user.click(screen.getByRole("button", { name: "30d" }));
    unmount();

    expect(cancel).toHaveBeenCalledWith(7);
    frame.mockRestore();
    cancel.mockRestore();
    expect(onChange).not.toHaveBeenCalled();
  });
});
