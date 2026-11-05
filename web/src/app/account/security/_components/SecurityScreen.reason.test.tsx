import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AccountSecurityView, CurrentUserView, PasskeyListView } from "@/api/types";
import type { SecurityReason } from "@/lib/navigation";
import { renderInLocale, textsIn } from "@/test/render";

import { SecurityScreen } from "./SecurityScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("./PasskeysCard", () => ({ PasskeysCard: () => null }));
vi.mock("./AuthenticatorCard", () => ({ AuthenticatorCard: () => null }));
vi.mock("./DevicesCard", () => ({ DevicesCard: () => null }));

const me = { user: { id: "user_admin", email: "admin@example.com", is_platform_admin: true } } as unknown as CurrentUserView;
const passkeys: PasskeyListView = { is_available: true, is_recommended: true, items: [] };
/** An admin signed in with the authenticator app alone. */
const appOnly: AccountSecurityView = {
  auth_level: "two_factor",
  is_mfa_required: false,
  recovery_codes_left: 10,
  passkey_count: 0,
  step_up_max_age_seconds: 600,
  totp_status: "active",
};

function renderScreen(security: AccountSecurityView, reason: SecurityReason, locale: "en" | "it" = "en") {
  return renderInLocale(
    <SecurityScreen me={me} initial={security} passkeys={passkeys} reason={reason} next="/admin" />,
    { locale },
  );
}

describe("SecurityScreen: why it was opened", () => {
  it("asks an admin with only the app for a passkey, with no way on yet", () => {
    const { t } = textsIn("en");
    renderScreen(appOnly, "admin_passkey");

    expect(screen.getByText(t("security.required.adminPasskey"))).toBeTruthy();
    expect(screen.queryByRole("link", { name: t("security.required.continue") })).toBeNull();
  });

  it("lets the admin continue once a passkey is there", () => {
    const { t } = textsIn("it");
    renderScreen({ ...appOnly, passkey_count: 1 }, "admin_passkey", "it");

    expect(screen.getByText(t("security.required.adminPasskey"))).toBeTruthy();
    expect(screen.getByRole("link", { name: t("security.required.continue") }).getAttribute("href")).toBe("/admin");
  });

  it("keeps the two-factor reasons as they were", () => {
    const { t } = textsIn("en");
    renderScreen(appOnly, "admin");

    expect(screen.getByText(t("security.required.admin"))).toBeTruthy();
    expect(screen.getByRole("link", { name: t("security.required.continue") })).toBeTruthy();
  });
});
