import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CurrentUserView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import { MoreSheet } from "./MoreSheet";

// The account panel has its own tests; here it is one place to go to.
vi.mock("./AccountPanel", () => ({
  AccountPanel: ({ onNavigate }: { onNavigate: () => void }) => (
    <button type="button" onClick={onNavigate}>
      Account
    </button>
  ),
}));

const { t } = textsIn("en");
const me = {} as CurrentUserView;

describe("the phone's More sheet", () => {
  it.each([
    ["×", async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: t("common.close") }))],
    ["Escape", async (user: ReturnType<typeof userEvent.setup>) => user.keyboard("{Escape}")],
    ["a place", async (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: "Account" }))],
  ])("starts to leave at the press (%s), before the shell closes it, and opens again whole", async (_, press) => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const sheet = (open: boolean) => <MoreSheet open={open} onClose={onClose} items={[]} me={me} />;
    const view = renderInLocale(sheet(true));
    const dialog = screen.getByRole("dialog", { name: t("navigation.more") }) as HTMLDialogElement;
    expect(dialog.hasAttribute("data-closing")).toBe(false);

    await press(user);
    // The press paints its answer at once; the shell's state closes the sheet a frame later.
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(dialog.hasAttribute("data-closing")).toBe(true);
    expect(dialog.open).toBe(true);

    view.rerender(sheet(false));
    expect(dialog.open).toBe(false);
    view.rerender(sheet(true));
    expect(dialog.open).toBe(true);
    expect(dialog.hasAttribute("data-closing")).toBe(false);
  });
});
