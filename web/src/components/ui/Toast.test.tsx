import { act, fireEvent, screen } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/errors";
import { renderInLocale } from "@/test/render";

import { UNDO_WINDOW_MS, useToast, type ToastApi } from "./Toast";

let toast: ToastApi;

/** Hands the toast API of the mounted provider to the test. */
function Grab() {
  const api = useToast();
  useEffect(() => {
    toast = api;
  }, [api]);
  return null;
}

function show(call: (api: ToastApi) => void) {
  act(() => call(toast));
}

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("offers Undo for five seconds and runs it once when pressed", () => {
    const onUndo = vi.fn();
    renderInLocale(<Grab />);
    show((api) => api.undoable("Booking cancelled", onUndo));

    const status = screen.getByRole("status");
    expect(status.textContent).toContain("Booking cancelled");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    expect(onUndo).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Booking cancelled")).toBeNull();
  });

  it("takes Undo away once its window has run out", () => {
    const onUndo = vi.fn();
    renderInLocale(<Grab />);
    show((api) => api.undoable("Lead closed", onUndo));

    act(() => vi.advanceTimersByTime(UNDO_WINDOW_MS - 1));
    expect(screen.getByRole("button", { name: "Undo" })).toBeTruthy();
    act(() => vi.advanceTimersByTime(1));

    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(onUndo).not.toHaveBeenCalled();
  });

  it("holds the Undo window while the pointer or the focus is on the toast", () => {
    renderInLocale(<Grab />);
    show((api) => api.undoable("Lead closed", () => undefined));
    const card = screen.getByRole("status");

    act(() => vi.advanceTimersByTime(4_000));
    fireEvent.pointerEnter(card);
    act(() => vi.advanceTimersByTime(60_000));
    expect(screen.getByRole("button", { name: "Undo" })).toBeTruthy();

    // The time left (one second) runs on once the pointer leaves.
    fireEvent.pointerLeave(card);
    act(() => vi.advanceTimersByTime(999));
    expect(screen.getByRole("button", { name: "Undo" })).toBeTruthy();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("speaks Undo in the interface language", () => {
    renderInLocale(<Grab />, { locale: "ka" });
    show((api) => api.undoable("…", () => undefined));

    expect(screen.getByRole("button", { name: "გაუქმება" })).toBeTruthy();
  });

  it("announces an error as an alert in the interface language, with its request id", () => {
    renderInLocale(<Grab />, { locale: "ru" });
    show((api) => api.error(new ApiError({ status: 500, code: "internal_error", detail: "boom", requestId: "req_42" })));

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("req_42");
    expect(alert.textContent).not.toContain("boom");
  });

  it("keeps a plain message its own time and shows at most four", () => {
    renderInLocale(<Grab />);
    show((api) => {
      for (const title of ["One", "Two", "Three", "Four", "Five"]) {
        api.success(title);
      }
    });

    expect(screen.getAllByRole("status").map((item) => item.textContent)).toEqual(["Two", "Three", "Four", "Five"]);
    fireEvent.pointerEnter(screen.getAllByRole("status")[0]!);
    act(() => vi.advanceTimersByTime(5_000));
    expect(screen.queryAllByRole("status")).toHaveLength(0);
  });

  it("moves into the topmost open modal dialog, whose outside is inert", () => {
    renderInLocale(
      <>
        <Grab />
        <dialog aria-label="Edit booking" />
      </>,
    );
    const dialog = screen.getByRole("dialog", { hidden: true });
    act(() => (dialog as HTMLDialogElement).showModal());
    show((api) => api.success("Saved"));

    expect(dialog.contains(screen.getByText("Saved"))).toBe(true);
  });
});
