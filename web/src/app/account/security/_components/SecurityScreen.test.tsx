import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { requestStepUp } from "@/api/stepUp";
import type { AccountSecurityView, CurrentUserView, PasskeyListView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import { SecurityScreen } from "./SecurityScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/api/stepUp", () => ({ requestStepUp: vi.fn(() => Promise.resolve(false)) }));
// The cards that ask the API by themselves are not what is checked here.
vi.mock("./PasskeysCard", () => ({ PasskeysCard: () => null }));
vi.mock("./AuthenticatorCard", () => ({ AuthenticatorCard: () => null }));
vi.mock("./DevicesCard", () => ({ DevicesCard: () => null }));

const me = { user: { id: "user_owner", email: "owner@example.com", is_platform_admin: false } } as unknown as CurrentUserView;
const passkeys: PasskeyListView = { is_available: true, is_recommended: false, items: [] };

/** A person whose only second factor is a passkey, on an older one-factor session. */
const passkeyOnly: AccountSecurityView = {
  auth_level: "one_factor",
  is_mfa_required: false,
  recovery_codes_left: 7,
  passkey_count: 1,
  step_up_max_age_seconds: 600,
  totp_status: null,
};

function renderScreen(security: AccountSecurityView) {
  return renderInLocale(
    <SecurityScreen me={me} initial={security} passkeys={passkeys} reason={null} next={null} />,
  );
}

describe("SecurityScreen: recovery codes and the session for every second factor", () => {
  it("shows a passkey person how many recovery codes are left", () => {
    const { t, tp } = textsIn("en");
    renderScreen(passkeyOnly);

    expect(screen.getByText(t("security.codes.title"))).toBeTruthy();
    expect(screen.getByText(tp("security.codes.left", 7))).toBeTruthy();
  });

  it("lets a passkey person count this session as two-factor", async () => {
    const { t } = textsIn("en");
    renderScreen(passkeyOnly);

    await userEvent.click(screen.getByRole("button", { name: t("security.session.upgrade") }));

    expect(vi.mocked(requestStepUp)).toHaveBeenCalledOnce();
  });

  it("offers neither to a person with no second factor", () => {
    const { t } = textsIn("en");
    renderScreen({ ...passkeyOnly, passkey_count: 0, recovery_codes_left: 0 });

    expect(screen.queryByText(t("security.codes.title"))).toBeNull();
    expect(screen.queryByRole("button", { name: t("security.session.upgrade") })).toBeNull();
  });
});
