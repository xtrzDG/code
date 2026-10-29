import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BUSINESS_SECTIONS, SECTION_LABELS, SECTION_TAB_LABELS } from "@/lib/sections";
import { LOCALES } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { IconCalendar, IconInbox } from "../icons";
import { PhoneTabBar } from "./PhoneTabBar";

describe("the phone tab bar", () => {
  it("names a section by its short tab name and marks the open one", () => {
    const { t } = textsIn("it");
    // The Italian inbox ("Conversazioni") is too long for a fifth of a phone.
    const inbox = t("navigation.sections.inbox");
    const inboxTab = t("navigation.tabLabels.inbox");
    const bookings = t("navigation.sections.bookings");
    expect(inboxTab).toBe("Chat");
    renderInLocale(
      <PhoneTabBar
        items={[
          { key: "inbox", href: "/b/business_1/inbox", label: inbox, tabLabel: inboxTab, icon: IconInbox, isActive: true },
          { key: "bookings", href: "/b/business_1/bookings", label: bookings, icon: IconCalendar, isActive: false },
        ]}
        isMoreActive={false}
        isMoreOpen={false}
        onOpenMore={() => undefined}
      />,
      { locale: "it" },
    );
    const bar = screen.getByRole("navigation", { name: t("navigation.tabBar") });
    expect(within(bar).getByRole("link", { name: inboxTab }).getAttribute("aria-current")).toBe("page");
    expect(within(bar).queryByText(inbox)).toBeNull();
    expect(within(bar).getByRole("link", { name: bookings })).toBeTruthy();
    // A word never breaks between letters: it is hyphenated or ends with "…".
    for (const label of bar.querySelectorAll("[data-tab-label]")) {
      expect(label.className).toContain("break-normal");
      expect(label.className).not.toContain("anywhere");
    }
  });

  it("lights More at the tap, before its sheet has opened, and while it is open", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    const onOpenMore = vi.fn();
    const items = [{ key: "inbox", href: "/b/business_1/inbox", label: "Inbox", icon: IconInbox, isActive: true }];
    const bar = (isMoreOpen: boolean) => <PhoneTabBar items={items} isMoreActive={false} isMoreOpen={isMoreOpen} onOpenMore={onOpenMore} />;
    const view = renderInLocale(bar(false));
    const more = screen.getByRole("button", { name: t("navigation.more") });
    const icon = () => more.querySelector("svg")?.getAttribute("class") ?? "";
    expect(icon()).toContain("text-ink-subtle");

    await user.click(more);
    // The shell opens the sheet after this paint; the tap has already answered.
    expect(onOpenMore).toHaveBeenCalledTimes(1);
    expect(icon()).toContain("text-accent");
    view.rerender(bar(true));
    expect(icon()).toContain("text-accent");
    view.rerender(bar(false));
    expect(icon()).toContain("text-ink-subtle");
  });

  it.each(LOCALES)("has a short name for every tab bar section in %s", (locale) => {
    const { t } = textsIn(locale);
    for (const section of BUSINESS_SECTIONS) {
      const key = SECTION_TAB_LABELS[section] ?? SECTION_LABELS[section];
      expect(t(key)).not.toBe(key);
    }
  });
});
