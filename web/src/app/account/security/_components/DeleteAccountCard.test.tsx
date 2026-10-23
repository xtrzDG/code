import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { CurrentUserView } from "@/api/types";
import { failure } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { DeleteAccountCard } from "./DeleteAccountCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const ACCOUNT = "nino@example.com";
const me = {
  user: { id: "user_1", email: ACCOUNT, is_platform_admin: false },
  memberships: [
    { business_id: "business_1", business_name: "Café Tbilisi", business_status: "live", country_code: "GE", role: "owner" },
  ],
} as unknown as CurrentUserView;

function refusal(code: string, details: string[]) {
  return failure(409, { error: "conflict", message: "You are the last owner.", reasons: [{ code, message: "", details }] });
}

async function deleteAccount() {
  const user = userEvent.setup();
  const { t } = textsIn("en");
  await user.click(screen.getByRole("button", { name: t("closure.account.action") }));
  const dialog = screen.getByRole("dialog", { name: t("closure.account.dialogTitle") });
  await user.type(within(dialog).getByRole("textbox"), ACCOUNT);
  await user.click(within(dialog).getByRole("button", { name: t("closure.account.confirm") }));
}

describe("DeleteAccountCard: Account → Security, the danger zone", () => {
  beforeEach(() => {
    vi.mocked(api.DELETE).mockReset();
  });

  it.each(["en", "ru", "ka", "he", "de"] as const)("says what deleting the account does, in %s", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<DeleteAccountCard me={me} account={ACCOUNT} />, { locale });

    const card = screen.getByTestId("delete-account");
    expect(card.textContent).toContain(t("closure.account.description"));
    expect(card.textContent).toContain(t("closure.account.ownerNote"));
    expect(within(card).getByRole("button", { name: t("closure.account.action") })).toBeTruthy();
  });

  it("names the businesses the person must close first", async () => {
    const { t } = textsIn("en");
    vi.mocked(api.DELETE).mockImplementation((() => refusal("last_business_owner", ["business_1"])) as never);
    renderInLocale(<DeleteAccountCard me={me} account={ACCOUNT} />);

    await deleteAccount();

    expect(vi.mocked(api.DELETE)).toHaveBeenCalledWith("/v1/me");
    const status = await screen.findByRole("status");
    await waitFor(() => expect(status.textContent).toBe(t("closure.account.lastOwner").replace("{names}", "Café Tbilisi")));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("sends the platform team to leave the team first, without a delete button", () => {
    const { t } = textsIn("en");
    renderInLocale(<DeleteAccountCard me={{ ...me, user: { ...me.user, is_platform_admin: true } }} account={ACCOUNT} />);

    expect(screen.getByText(t("closure.account.platformNote"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("closure.account.action") })).toBeNull();
  });
});
