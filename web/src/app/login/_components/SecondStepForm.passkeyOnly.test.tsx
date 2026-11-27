import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SecondStepRequired } from "@/api/auth";
import type { MfaChallengeView } from "@/api/types";
import { usePasskeySupport } from "@/lib/security/usePasskeySupport";
import { renderInLocale, textsIn } from "@/test/render";

import { SecondStepForm } from "./SecondStepForm";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/lib/security/usePasskeySupport", () => ({ usePasskeySupport: vi.fn() }));

/** The second step a login code's answer asks for: how it is answered, or (no factor yet) set up. */
function secondStep(challenge: Partial<MfaChallengeView>): SecondStepRequired {
  return {
    mfa_required: true,
    is_new_user: false,
    mfa_challenge: {
      mfa_challenge_id: "mfa_1",
      expires_in_seconds: 300,
      requires_enrollment: false,
      methods: [],
      enrollment_methods: [],
      ...challenge,
    },
  };
}

function renderStep(challenge: Partial<MfaChallengeView>, locale: "en" | "it" = "en") {
  renderInLocale(
    <SecondStepForm step={secondStep(challenge)} next="/admin" account="admin@example.com" onStartOver={vi.fn()} />,
    { locale },
  );
}

/** A sign-in step asking a platform admin without a factor to set one up. */
function renderEnrollment(enrollmentMethods: MfaChallengeView["enrollment_methods"], locale: "en" | "it" = "en") {
  renderStep({ requires_enrollment: true, enrollment_methods: enrollmentMethods }, locale);
}

describe("SecondStepForm: platform admins held to passkeys (production)", () => {
  beforeEach(() => {
    vi.mocked(usePasskeySupport).mockReturnValue(true);
  });

  it.each(["en", "it"] as const)("offers the passkey alone when the app is not allowed (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderEnrollment(["passkey"], locale);

    expect(screen.getByRole("button", { name: t("passkeys.enrollment.add") })).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.enrollment.useApp") })).toBeNull();
    expect(screen.getByText(t("passkeys.enrollment.passkeyRequired"))).toBeTruthy();
  });

  it("still offers the app where it is allowed (development, other people)", () => {
    const { t } = textsIn("en");
    renderEnrollment(["passkey", "totp"]);

    expect(screen.getByRole("button", { name: t("passkeys.enrollment.useApp") })).toBeTruthy();
    expect(screen.getByText(t("passkeys.enrollment.description"))).toBeTruthy();
  });

  it("says a passkey is needed in a browser that cannot make one, without an app to fall back to", () => {
    const { t } = textsIn("en");
    vi.mocked(usePasskeySupport).mockReturnValue(false);
    renderEnrollment(["passkey"]);

    expect(screen.getByText(t("passkeys.enrollment.passkeyOnly"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("mfa.enrollment.start") })).toBeNull();
    expect(screen.getByRole("button", { name: t("mfa.secondStep.startOver") })).toBeTruthy();
  });
});

describe("SecondStepForm: the code form follows the step's methods", () => {
  // The sign-in's own calls (src/api/auth.ts) go through fetch: kept waiting here.
  const sent = vi.fn<typeof fetch>(() => new Promise<Response>(() => undefined));

  beforeEach(() => {
    vi.mocked(usePasskeySupport).mockReturnValue(true);
    sent.mockClear();
    vi.stubGlobal("fetch", sent);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each(["en", "it"] as const)(
    "gives a passkey person without the app (an admin held to passkeys) the recovery code field (%s)",
    async (locale) => {
      const { t } = textsIn(locale);
      renderStep({ methods: ["passkey", "recovery_code"] }, locale);

      await userEvent.click(screen.getByRole("button", { name: t("passkeys.signIn.useCode") }));

      expect(document.activeElement).toBe(screen.getByLabelText(t("mfa.secondStep.recoveryCode")));
      expect(screen.getByText(t("mfa.secondStep.recoveryDescription"))).toBeTruthy();
      expect(screen.queryByLabelText(t("mfa.secondStep.code"))).toBeNull();
      expect(screen.queryByRole("button", { name: t("mfa.secondStep.useApp") })).toBeNull();
      expect(screen.queryByRole("button", { name: t("mfa.secondStep.useRecovery") })).toBeNull();
      expect(screen.getByRole("button", { name: t("passkeys.signIn.usePasskey") })).toBeTruthy();
    },
  );

  it("signs in with the recovery code typed, never an app code", async () => {
    const { t } = textsIn("en");
    renderStep({ methods: ["passkey", "recovery_code"] });
    await userEvent.click(screen.getByRole("button", { name: t("passkeys.signIn.useCode") }));

    await userEvent.type(screen.getByLabelText(t("mfa.secondStep.recoveryCode")), "abcd-efgh-jkmn");
    await userEvent.click(screen.getByRole("button", { name: t("mfa.secondStep.verify") }));

    expect(sent).toHaveBeenCalledTimes(1);
    const [path, init] = sent.mock.calls[0] ?? [];
    expect(path).toBe("/api/auth/mfa/verify");
    expect(JSON.parse(String(init?.body))).toEqual({ mfa_challenge_id: "mfa_1", recovery_code: "abcd-efgh-jkmn" });
  });

  it.each([
    { methods: ["passkey", "recovery_code"], passkeys: false },
    { methods: ["recovery_code"], passkeys: true },
  ] as const)(
    "opens on the recovery code field where no passkey can sign: $methods, passkeys here $passkeys",
    ({ methods, passkeys }) => {
      const { t } = textsIn("en");
      vi.mocked(usePasskeySupport).mockReturnValue(passkeys);
      renderStep({ methods: [...methods] });

      expect(screen.getByLabelText(t("mfa.secondStep.recoveryCode"))).toBeTruthy();
      expect(screen.queryByLabelText(t("mfa.secondStep.code"))).toBeNull();
      expect(screen.queryByRole("button", { name: t("mfa.secondStep.useApp") })).toBeNull();
      expect(screen.queryByRole("button", { name: t("passkeys.signIn.usePasskey") })).toBeNull();
    },
  );

  it("keeps the app's code, the switch to a recovery code and back for a person with the app and a passkey", async () => {
    const { t } = textsIn("en");
    renderStep({ methods: ["passkey", "totp", "recovery_code"] });

    await userEvent.click(screen.getByRole("button", { name: t("passkeys.signIn.useCode") }));

    expect(document.activeElement).toBe(screen.getByLabelText(t("mfa.secondStep.code")));
    expect(screen.getByRole("button", { name: t("passkeys.signIn.usePasskey") })).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: t("mfa.secondStep.useRecovery") }));
    expect(screen.getByLabelText(t("mfa.secondStep.recoveryCode"))).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: t("mfa.secondStep.useApp") }));
    expect(screen.getByLabelText(t("mfa.secondStep.code"))).toBeTruthy();
  });

  it("keeps the app's code first, with the switch to a recovery code, for a person with the app alone", async () => {
    const { t } = textsIn("en");
    renderStep({ methods: ["totp", "recovery_code"] });

    expect(document.activeElement).toBe(screen.getByLabelText(t("mfa.secondStep.code")));
    expect(screen.getByText(t("mfa.secondStep.description"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.signIn.use") })).toBeNull();
    expect(screen.queryByRole("button", { name: t("passkeys.signIn.usePasskey") })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: t("mfa.secondStep.useRecovery") }));
    expect(screen.getByLabelText(t("mfa.secondStep.recoveryCode"))).toBeTruthy();
    expect(screen.getByRole("button", { name: t("mfa.secondStep.useApp") })).toBeTruthy();
  });

  it.each([true, null])("offers no code form for a passkey alone (passkeys in this browser: %s)", (passkeys) => {
    // null: not known yet (the first paint never claims a passkey cannot be used).
    const { t } = textsIn("en");
    vi.mocked(usePasskeySupport).mockReturnValue(passkeys);
    renderStep({ methods: ["passkey"] });

    expect(screen.getByRole("button", { name: t("passkeys.signIn.use") })).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.signIn.useCode") })).toBeNull();
    expect(screen.queryByLabelText(t("mfa.secondStep.code"))).toBeNull();
    expect(screen.queryByLabelText(t("mfa.secondStep.recoveryCode"))).toBeNull();
    expect(screen.queryByRole("button", { name: t("mfa.secondStep.useRecovery") })).toBeNull();
    expect(screen.queryByText(t("passkeys.signIn.unsupported"))).toBeNull();
    expect(screen.getByRole("button", { name: t("mfa.secondStep.startOver") })).toBeTruthy();
  });

  it.each([
    { methods: ["passkey"], passkeys: false, locale: "en", text: "passkeys.signIn.unsupported" },
    { methods: ["passkey"], passkeys: false, locale: "it", text: "passkeys.signIn.unsupported" },
    { methods: [], passkeys: true, locale: "en", text: "passkeys.signIn.noWay" },
    { methods: [], passkeys: false, locale: "it", text: "passkeys.signIn.noWay" },
  ] as const)(
    "says why nothing here can answer the step and offers only to sign in again: $methods, passkeys here $passkeys ($locale)",
    ({ methods, passkeys, locale, text }) => {
      const { t } = textsIn(locale);
      vi.mocked(usePasskeySupport).mockReturnValue(passkeys);
      renderStep({ methods: [...methods] }, locale);

      expect(screen.getByText(t(text))).toBeTruthy();
      // No passkey button that would ask the API for a challenge, no code form.
      expect(screen.getAllByRole("button")).toHaveLength(1);
      expect(screen.getByRole("button", { name: t("mfa.secondStep.startOver") })).toBeTruthy();
      expect(screen.queryByRole("textbox")).toBeNull();
      expect(sent).not.toHaveBeenCalled();
    },
  );
});
