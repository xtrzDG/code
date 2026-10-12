import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { UserMembershipView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import { BusinessSwitcherGroups } from "./BusinessSwitcherGroups";

const membership = (business_id: string, business_name: string, brand?: { id: string; name: string }): UserMembershipView =>
  ({
    business_id,
    business_name,
    business_status: "live",
    country_code: "GE",
    role: "owner",
    brand_id: brand?.id ?? null,
    brand_name: brand?.name ?? null,
  }) as UserMembershipView;

const brand = { id: "brand_1", name: "Mtsvane Ezo" };

describe("the business switcher's groups", () => {
  it("lists a brand's locations under its name, then the other businesses", () => {
    const { t } = textsIn("en");
    renderInLocale(
      <BusinessSwitcherGroups
        memberships={[membership("b1", "Vake", brand), membership("b2", "Café Solo"), membership("b3", "Saburtalo", brand)]}
        currentBusinessId="b3"
        pathname="/b/b3/inbox"
        onNavigate={() => undefined}
      />,
      { locale: "en" },
    );
    const chain = screen.getByRole("group", { name: "Mtsvane Ezo" });
    expect(within(chain).getAllByRole("link").map((link) => link.textContent)).toEqual([
      t("brands.switcher.overview"),
      expect.stringContaining("Vake"),
      expect.stringContaining("Saburtalo"),
    ]);
    expect(within(chain).getByRole("link", { name: t("brands.switcher.overview") }).getAttribute("href")).toBe("/brands/brand_1");
    // The same page in the other location: the inbox stays the inbox.
    expect(within(chain).getByRole("link", { name: /Vake/ }).getAttribute("href")).toBe("/b/b1/inbox");
    expect(within(chain).getByRole("link", { name: /Saburtalo/ }).getAttribute("aria-current")).toBe("page");
    const others = screen.getByRole("group", { name: t("brands.switcher.others") });
    expect(within(others).getByRole("link", { name: /Café Solo/ })).toBeTruthy();
  });

  it("keeps one plain list when no business is in a brand", () => {
    const { t } = textsIn("en");
    renderInLocale(
      <BusinessSwitcherGroups
        memberships={[membership("b1", "Vake"), membership("b2", "Café Solo")]}
        currentBusinessId="b1"
        pathname="/b/b1/overview"
        onNavigate={() => undefined}
      />,
      { locale: "en" },
    );
    expect(screen.queryByText(t("brands.switcher.others"))).toBeNull();
    expect(screen.queryByText(t("brands.switcher.overview"))).toBeNull();
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });
});
