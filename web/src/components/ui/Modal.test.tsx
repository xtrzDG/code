import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { renderInLocale } from "@/test/render";

import { Button } from "./Button";
import { Modal } from "./Modal";
import { DIALOG_CLOSE_MS } from "./useClosingContent";

function Page({ onClose = () => undefined, initiallyOpen = false }: { onClose?: () => void; initiallyOpen?: boolean }) {
  const [isOpen, setOpen] = useState(initiallyOpen);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open
      </button>
      <a href="#behind">Behind</a>
      <Modal
        open={isOpen}
        title="New business"
        description="Name it the way customers know it."
        onClose={() => {
          onClose();
          setOpen(false);
        }}
        footer={<Button onClick={() => setOpen(false)}>Save</Button>}
      >
        <label>
          Name <input name="name" />
        </label>
      </Modal>
    </>
  );
}

describe("Modal", () => {
  it("opens as a modal dialog: focus moves inside and the page behind is inert", async () => {
    const user = userEvent.setup();
    const showModal = vi.spyOn(HTMLDialogElement.prototype, "showModal");
    renderInLocale(<Page />);

    await user.click(screen.getByRole("button", { name: "Open" }));

    expect(showModal).toHaveBeenCalledTimes(1);
    const dialog = screen.getByRole("dialog", { name: "New business" });
    expect(dialog.matches(":modal")).toBe(true);
    expect(dialog).toHaveProperty("open", true);
    expect(dialog.contains(document.activeElement)).toBe(true);
    // Everything focusable outside the dialog sits in an inert subtree.
    for (const outside of [screen.getByRole("button", { name: "Open", hidden: true }), screen.getByText("Behind")]) {
      expect(outside.closest("[inert]")).not.toBeNull();
    }
    expect(dialog.closest("[inert]")).toBeNull();
  });

  it("names itself by its title and description", () => {
    renderInLocale(<Page initiallyOpen />);

    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-labelledby")).toBe(screen.getByRole("heading", { name: "New business" }).id);
    expect(document.getElementById(dialog.getAttribute("aria-describedby") ?? "")?.textContent).toBe("Name it the way customers know it.");
  });

  it("closes on Escape, calling onClose once and returning focus to the opener", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderInLocale(<Page onClose={onClose} />);
    const opener = screen.getByRole("button", { name: "Open" });
    await user.click(opener);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(opener);
    expect(opener.closest("[inert]")).toBeNull();
  });

  it("closes from its close button, labelled in the interface language", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderInLocale(<Page onClose={onClose} initiallyOpen />, { locale: "ru" });

    await user.click(screen.getByRole("button", { name: "Закрыть" }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("closes on a press on the backdrop, never on one inside", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderInLocale(<Page onClose={onClose} initiallyOpen />);

    await user.click(screen.getByRole("textbox", { name: "Name" }));
    expect(onClose).not.toHaveBeenCalled();

    // The backdrop is the <dialog> element itself.
    await user.pointer({ keys: "[MouseLeft]", target: screen.getByRole("dialog") });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when the screen closes it", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderInLocale(<Page onClose={onClose} initiallyOpen />);

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("keeps what it showed while it fades out, then empties", () => {
    vi.useFakeTimers();
    const view = renderInLocale(
      <Modal open title="Delete booking" onClose={() => undefined}>
        <p>Anna, 19:00</p>
      </Modal>,
    );

    // The screen clears what the dialog was about as it closes it.
    view.rerender(
      <Modal open={false} title="" onClose={() => undefined}>
        {null}
      </Modal>,
    );
    const dialog = document.querySelector("dialog");
    expect(dialog?.textContent).toContain("Delete booking");
    expect(dialog?.textContent).toContain("Anna, 19:00");

    act(() => vi.advanceTimersByTime(DIALOG_CLOSE_MS));
    expect(dialog?.textContent).toBe("");
    vi.useRealTimers();
  });
});
