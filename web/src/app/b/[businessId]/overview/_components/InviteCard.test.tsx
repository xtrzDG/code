import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale } from "@/test/render";

import { InviteCard } from "./InviteCard";
import { PhoneFolds } from "./PhoneFold";

const program = vi.hoisted(() => ({ data: { is_invite_card_due: true } as { is_invite_card_due: boolean } | undefined }));

vi.mock("@/components/referrals/useReferralProgram", () => ({ useReferralProgram: () => ({ program }) }));
vi.mock("@/components/referrals/InviteLinkPanel", () => ({ InviteLinkPanel: () => <p>The invitation link</p> }));

const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "GEL" } as unknown as BusinessView;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

function Overview() {
  return (
    <BusinessProvider business={business} me={me}>
      <PhoneFolds>
        <InviteCard />
      </PhoneFolds>
    </BusinessProvider>
  );
}

describe("InviteCard", () => {
  afterEach(() => {
    window.localStorage.clear();
    program.data = { is_invite_card_due: true };
  });

  it("folds into one row on a phone that opens the invitation on a tap", async () => {
    const user = userEvent.setup();
    renderInLocale(<Overview />);
    const row = screen.getByRole("button", { name: /^Invite a business — a month free/ });
    const content = document.getElementById(row.getAttribute("aria-controls")!)!;
    expect(row.getAttribute("aria-expanded")).toBe("false");
    expect(content.className).toContain("max-lg:hidden");
    expect(content.textContent).toContain("The invitation link");

    await user.click(row);
    expect(row.getAttribute("aria-expanded")).toBe("true");
    expect(content.className).not.toContain("max-lg:hidden");
    expect(screen.getByRole("region", { name: "Invite a business — a month free" })).toBeTruthy();
  });

  it("shows no row before the invitation is due", () => {
    program.data = { is_invite_card_due: false };
    renderInLocale(<Overview />);
    expect(screen.queryByRole("button", { name: /^Invite a business/ })).toBeNull();
  });
});
