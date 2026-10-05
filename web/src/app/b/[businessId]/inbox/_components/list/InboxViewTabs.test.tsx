import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { InboxView } from "@/lib/navigation";
import { renderInLocale, textsIn } from "@/test/render";

import type { InboxViewCounts } from "../../_lib/types";
import { InboxViewTabs } from "./InboxViewTabs";

const COUNTS = { needs_person: 2, requests: 1, mine: 0, unassigned: 3 } as unknown as InboxViewCounts;
/** The list column beside an open conversation is about 360 px; three tabs need about 600. */
const COLUMN_WIDTH = 360;
const TABS_WIDTH = 600;

function Tabs({ initial, onChange = () => undefined }: { initial: InboxView; onChange?: (view: InboxView) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <div style={{ width: COLUMN_WIDTH }}>
      <InboxViewTabs
        value={value}
        counts={COUNTS}
        onChange={(view) => {
          onChange(view);
          setValue(view);
        }}
      />
    </div>
  );
}

/** jsdom has no layout: the scrolling row reports the narrow column's geometry. */
function narrowColumn() {
  const isRow = (element: Element) => element.hasAttribute("data-scroll-row");
  const clientWidth = vi.spyOn(HTMLElement.prototype, "clientWidth", "get");
  clientWidth.mockImplementation(function width(this: HTMLElement) {
    return isRow(this) ? COLUMN_WIDTH : 0;
  });
  const scrollWidth = vi.spyOn(HTMLElement.prototype, "scrollWidth", "get");
  scrollWidth.mockImplementation(function width(this: HTMLElement) {
    return isRow(this) ? TABS_WIDTH : 0;
  });
}

function chosenTab(view: InboxView): HTMLElement {
  return document.querySelector<HTMLElement>(`label[data-inbox-view="${view}"]`)!;
}

describe("InboxViewTabs in the 360 px list column", () => {
  let scrolled: Element[];

  beforeEach(() => {
    narrowColumn();
    scrolled = [];
    vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(function record(this: Element) {
      scrolled.push(this);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("scrolls the chosen tab into sight and fades the side that is cut", () => {
    renderInLocale(<Tabs initial="mine" />, { locale: "ru" });

    expect(scrolled.at(-1)).toBe(chosenTab("mine"));
    const row = document.querySelector("[data-scroll-row]")!;
    expect(row.hasAttribute("data-fade-right")).toBe(true);
    // The chosen tab is a whole label: nothing truncates or hides it.
    expect(chosenTab("mine").className).not.toMatch(/truncate|hidden|overflow-hidden/);
  });

  it("follows the choice: each newly chosen tab is scrolled into sight", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("ru");
    renderInLocale(<Tabs initial="mine" />, { locale: "ru" });

    await user.click(screen.getByRole("radio", { name: new RegExp(t("inbox.views.needs_person")) }));

    expect(scrolled.at(-1)).toBe(chosenTab("needs_person"));
    expect(screen.getByRole("radio", { name: new RegExp(t("inbox.views.needs_person")) })).toHaveProperty("checked", true);
  });

  it.each(["unassigned", "all"] as const)("shows a view chosen under More (%s) in full on the More button", (view) => {
    const { t } = textsIn("ru");
    renderInLocale(<Tabs initial={view} />, { locale: "ru" });

    const more = document.querySelector<HTMLElement>("[data-more-views]")!;
    expect(more.getAttribute("data-chosen")).toBe(view);
    expect(more.textContent).toContain(t(`inbox.views.${view}`));
    // It sits outside the scrolling row, so it is never scrolled away or cut.
    expect(more.closest("[data-scroll-row]")).toBeNull();
    expect(more.className).not.toMatch(/truncate/);
    // No primary tab claims the choice.
    expect(screen.getAllByRole("radio").every((radio) => !(radio as HTMLInputElement).checked)).toBe(true);
  });

  it("chooses from More with the keyboard and gives the focus back to the button", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { t } = textsIn("en");
    renderInLocale(<Tabs initial="requests" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: new RegExp(t("inbox.moreViews")) }));
    const menu = screen.getByRole("menu", { name: t("inbox.moreViews") });
    expect(document.activeElement).toBe(within(menu).getAllByRole("menuitemradio")[0]);
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenCalledWith("all");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(document.activeElement).toBe(document.querySelector("[data-more-views]"));
    expect(document.querySelector("[data-more-views]")?.getAttribute("data-chosen")).toBe("all");
  });

  it("closes More on Escape without changing the view", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderInLocale(<Tabs initial="requests" onChange={onChange} />);

    await user.click(document.querySelector<HTMLElement>("[data-more-views]")!);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("menu")).toBeNull();
    expect(onChange).not.toHaveBeenCalled();
  });
});
