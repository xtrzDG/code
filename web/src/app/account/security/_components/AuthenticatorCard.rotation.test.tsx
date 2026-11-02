import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { AccountSecurityView } from "@/api/types";
import { ViewerTimeZoneProvider } from "@/components/time/ViewerTimeZone";
import { renderInLocale, textsIn } from "@/test/render";

import { AuthenticatorCard } from "./AuthenticatorCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const TICKET = "q3Jt0bW8yJ1x2Zc4l5mN6oP7rS8tU9vW0xY1zA2bC3d";
const CODES = Array.from({ length: 10 }, (_, index) => `test-code-000${index}`);

const NO_APP: AccountSecurityView = {
  is_mfa_required: false,
  recovery_codes_left: 0,
  passkey_count: 0,
  step_up_max_age_seconds: 600,
  totp_status: null,
};

/** What openapi-fetch resolves to for a 200. */
function answer(data: unknown): never {
  return Promise.resolve({ data, response: new Response(null, { status: 200 }) }) as never;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.mocked(api.POST).mockReset();
});

async function setUpTheApp(confirmed: object, onChanged: () => Promise<void>) {
  const { t } = textsIn("en");
  vi.mocked(api.POST)
    .mockReturnValueOnce(
      answer({
        secret: "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
        provisioning_uri: "otpauth://totp/Assistant%20Workshop:owner?secret=JBSWY3DPEHPK3PXP",
        issuer: "Assistant Workshop",
        account_label: "owner@example.com",
      }),
    )
    .mockReturnValueOnce(answer(confirmed));
  renderInLocale(
    <ViewerTimeZoneProvider initialZone="Europe/Rome">
      <AuthenticatorCard security={NO_APP} account="owner@example.com" onChanged={onChanged} />
    </ViewerTimeZoneProvider>,
    { locale: "en" },
  );
  fireEvent.click(screen.getByRole("button", { name: t("security.app.setUp") }));
  await userEvent.type(await screen.findByLabelText(t("mfa.setup.code")), "123456");
  await screen.findByRole("dialog", { name: t("mfa.recovery.title") });
}

describe("AuthenticatorCard: a new app that raised the session swaps its token", () => {
  it("sends the answer's ticket before the page reloads its security state", async () => {
    const rotations = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", rotations);
    const onChanged = vi.fn(async () => undefined);

    await setUpTheApp({ recovery_codes: CODES, is_level_raised: true, rotation_ticket: TICKET }, onChanged);

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(rotations).toHaveBeenCalledWith("/api/auth/session/rotate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rotation_ticket: TICKET }),
    });
    expect(rotations.mock.invocationCallOrder[0]).toBeLessThan(onChanged.mock.invocationCallOrder[0] ?? 0);
  });

  it("keeps the token when the session already had two factors", async () => {
    const rotations = vi.fn();
    vi.stubGlobal("fetch", rotations);
    const onChanged = vi.fn(async () => undefined);

    await setUpTheApp({ recovery_codes: CODES, is_level_raised: false, rotation_ticket: null }, onChanged);

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(rotations).not.toHaveBeenCalled();
  });
});
