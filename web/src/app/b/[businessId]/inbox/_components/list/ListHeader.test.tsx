import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { ListHeader } from "./ListHeader";

type Props = ComponentProps<typeof ListHeader>;

function header(overrides: Partial<Props> = {}) {
  const props: Props = {
    density: "comfortable",
    onDensity: vi.fn(),
    selection: "none",
    selectedCount: 0,
    canSelect: true,
    isResolving: false,
    onToggleAll: vi.fn(),
    onResolve: vi.fn(),
    onClear: vi.fn(),
    onShortcuts: vi.fn(),
    ...overrides,
  };
  return { props, view: renderInLocale(<ListHeader {...props} />) };
}

const { t, tp } = textsIn("en");

describe("ListHeader", () => {
  it("offers the density, the keys and a box for all while nothing is selected", async () => {
    const { props } = header();
    expect(screen.getByRole<HTMLInputElement>("radio", { name: t("inboxTriage.density.comfortable") }).checked).toBe(true);
    await userEvent.click(screen.getByRole("radio", { name: t("inboxTriage.density.compact") }));
    expect(props.onDensity).toHaveBeenCalledWith("compact");

    await userEvent.click(screen.getByRole("button", { name: t("inboxTriage.keys.open") }));
    expect(props.onShortcuts).toHaveBeenCalledOnce();

    const all = screen.getByRole<HTMLInputElement>("checkbox", { name: t("inboxTriage.select.all") });
    expect(all.checked).toBe(false);
    await userEvent.click(all);
    expect(props.onToggleAll).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: t("inboxTriage.select.resolve") })).toBeNull();
  });

  it("has no box for all when no row has anything to resolve", () => {
    header({ canSelect: false });
    expect(screen.queryByRole("checkbox", { name: t("inboxTriage.select.all") })).toBeNull();
  });

  it("with a selection says how many, resolves them and clears them", async () => {
    const { props } = header({ selection: "some", selectedCount: 2 });
    expect(screen.getByText(tp("inboxTriage.select.count", 2)).getAttribute("aria-live")).toBe("polite");
    const all = screen.getByRole<HTMLInputElement>("checkbox", { name: t("inboxTriage.select.all") });
    expect(all.indeterminate).toBe(true);
    expect(screen.queryByRole("radio", { name: t("inboxTriage.density.compact") })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: t("inboxTriage.select.resolve") }));
    expect(props.onResolve).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: t("inboxTriage.select.clear") }));
    expect(props.onClear).toHaveBeenCalledOnce();
  });

  it("checks the box for all when every row with something to resolve is selected", () => {
    header({ selection: "all", selectedCount: 3 });
    const all = screen.getByRole<HTMLInputElement>("checkbox", { name: t("inboxTriage.select.all") });
    expect(all.checked).toBe(true);
    expect(all.indeterminate).toBe(false);
  });
});
