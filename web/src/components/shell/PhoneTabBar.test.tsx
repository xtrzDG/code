import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BUSINESS_SECTIONS, SECTION_LABELS, SECTION_TAB_LABELS } from "@/lib/sections";
import { LOCALES } from "@/i18n/config";
import { renderInLocale, textsIn } from "@/test/render";

import { IconCalendar, IconInbox } from "../icons";
import { PhoneTabBar } from "./PhoneTabBar";

describe("the phone tab bar", () => {
  it("names a section by its short tab name and marks the open one", () => {
    const { t } = textsIn("de");
    // The German inbox ("Posteingang") is too long for a fifth of a phone.
    expect(t("navigation.tabLabels.inbox")).toBe("Eingang");
    renderInLocale(
      <PhoneTabBar
        items={[
          { key: "inbox", href: "/b/business_1/inbox", label: "Posteingang", tabLabel: "Eingang", icon: IconInbox, isActive: true },
          { key: "bookings", href: "/b/business_1/bookings", label: "Buchungen", icon: IconCalendar, isActive: false },
        ]}
        isMoreActive={false}
        isMoreOpen={false}
        onOpenMore={() => undefined}
      />,
      { locale: "de" },
    );
    const bar = screen.getByRole("navigation", { name: t("navigation.tabBar") });
    expect(within(bar).getByRole("link", { name: "Eingang" }).getAttribute("aria-current")).toBe("page");
    expect(within(bar).queryByText("Posteingang")).toBeNull();
    expect(within(bar).getByRole("link", { name: "Buchungen" })).toBeTruthy();
    // A word never breaks between letters: it is hyphenated or ends with "…".
    for (const label of bar.querySelectorAll("[data-tab-label]")) {
      expect(label.className).toContain("break-normal");
      expect(label.className).not.toContain("anywhere");
    }
  });

  it.each(LOCALES)("has a short name for every tab bar section in %s", (locale) => {
    const { t } = textsIn(locale);
    for (const section of BUSINESS_SECTIONS) {
      const key = SECTION_TAB_LABELS[section] ?? SECTION_LABELS[section];
      expect(t(key)).not.toBe(key);
    }
  });
});
