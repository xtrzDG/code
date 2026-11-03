import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SecondStepRequired } from "@/api/auth";
import { usePasskeySupport } from "@/lib/security/usePasskeySupport";
import { renderInLocale, textsIn } from "@/test/render";

import { SecondStepForm } from "./SecondStepForm";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/lib/security/usePasskeySupport", () => ({ usePasskeySupport: vi.fn() }));

/** A sign-in step asking a platform admin without a factor to set one up. */
function enrollmentStep(enrollmentMethods: ("passkey" | "totp")[]): SecondStepRequired {
  return {
    mfa_required: true,
    is_new_user: false,
    mfa_challenge: {
      mfa_challenge_id: "mfa_1",
      expires_in_seconds: 300,
      requires_enrollment: true,
      methods: [],
      enrollment_methods: enrollmentMethods,
    },
  } as SecondStepRequired;
}

function renderStep(enrollmentMethods: ("passkey" | "totp")[], locale: "en" | "it" = "en") {
  renderInLocale(
    <SecondStepForm step={enrollmentStep(enrollmentMethods)} next="/admin" account="admin@example.com" onStartOver={vi.fn()} />,
    { locale },
  );
}

describe("SecondStepForm: platform admins held to passkeys (production)", () => {
  beforeEach(() => {
    vi.mocked(usePasskeySupport).mockReturnValue(true);
  });

  it.each(["en", "it"] as const)("offers the passkey alone when the app is not allowed (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderStep(["passkey"], locale);

    expect(screen.getByRole("button", { name: t("passkeys.enrollment.add") })).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.enrollment.useApp") })).toBeNull();
    expect(screen.getByText(t("passkeys.enrollment.passkeyRequired"))).toBeTruthy();
  });

  it("still offers the app where it is allowed (development, other people)", () => {
    const { t } = textsIn("en");
    renderStep(["passkey", "totp"]);

    expect(screen.getByRole("button", { name: t("passkeys.enrollment.useApp") })).toBeTruthy();
    expect(screen.getByText(t("passkeys.enrollment.description"))).toBeTruthy();
  });

  it("says a passkey is needed in a browser that cannot make one, without an app to fall back to", () => {
    const { t } = textsIn("en");
    vi.mocked(usePasskeySupport).mockReturnValue(false);
    renderStep(["passkey"]);

    expect(screen.getByText(t("passkeys.enrollment.passkeyOnly"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("mfa.enrollment.start") })).toBeNull();
    expect(screen.getByRole("button", { name: t("mfa.secondStep.startOver") })).toBeTruthy();
  });
});
