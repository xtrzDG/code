import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { settleStepUp } from "@/api/stepUp";
import type { StepUpChallengeView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import StepUpForm from "./StepUpForm";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/api/stepUp", () => ({ settleStepUp: vi.fn() }));

/** What openapi-fetch resolves to for a 200. */
function answer(data: unknown): never {
  return Promise.resolve({ data, response: new Response(null, { status: 200 }) }) as never;
}

const VERIFIED = { auth_level: "two_factor", authenticated_at: 1, step_up_valid_until: 2, is_level_raised: false };

function answerStepUp(challenge: StepUpChallengeView, verified: object = VERIFIED) {
  vi.mocked(api.POST).mockImplementation(((path: string) =>
    answer(path === "/v1/auth/step-up" ? challenge : verified)) as never);
}

function postsTo(path: string): unknown[][] {
  return vi.mocked(api.POST).mock.calls.filter((call) => call[0] === path);
}

describe("StepUpForm: a passkey person confirms with a second factor, never a login code", () => {
  beforeEach(() => {
    vi.mocked(api.POST).mockReset();
  });

  // jsdom has no WebAuthn, as a browser without passkeys.
  it.each([
    { method: "passkey", passkey_available: true },
    { method: "recovery_code", passkey_available: false },
  ] as const)("asks for a recovery code when $method cannot be used here", async (challenge) => {
    const { t } = textsIn("en");
    answerStepUp(challenge);
    renderInLocale(<StepUpForm />);

    await userEvent.type(await screen.findByLabelText(t("mfa.secondStep.recoveryCode")), "abcd-efgh");
    await userEvent.click(screen.getByRole("button", { name: t("mfa.stepUp.confirm") }));

    await waitFor(() => expect(postsTo("/v1/auth/step-up/verify")).toHaveLength(1));
    expect(postsTo("/v1/auth/step-up/verify")[0]?.[1]).toEqual({ body: { recovery_code: "abcd-efgh" } });
    // Asked once, without asking for a login code to be sent.
    expect(postsTo("/v1/auth/step-up")).toEqual([["/v1/auth/step-up"]]);
    expect(screen.queryByRole("button", { name: t("mfa.stepUp.resend") })).toBeNull();
  });

  it("confirms a person with no second factor with the login code sent", async () => {
    const { t } = textsIn("en");
    answerStepUp({
      method: "login_code",
      passkey_available: false,
      login_code: { challenge_id: "otp_1", masked_destination: "o***@example.com", expires_in_seconds: 300 },
    } as StepUpChallengeView);
    renderInLocale(<StepUpForm />);

    expect(await screen.findByRole("button", { name: t("mfa.stepUp.resend") })).toBeTruthy();
    expect(screen.queryByLabelText(t("mfa.secondStep.recoveryCode"))).toBeNull();
  });
});

const ROTATION_TICKET = "q3Jt0bW8yJ1x2Zc4l5mN6oP7rS8tU9vW0xY1zA2bC3d";

describe("StepUpForm: a confirmation that raised the session to two factors swaps its token", () => {
  const rotations = vi.fn(async () => new Response(null, { status: 200 }));

  beforeEach(() => {
    vi.mocked(api.POST).mockReset();
    vi.mocked(settleStepUp).mockClear();
    rotations.mockClear();
    vi.stubGlobal("fetch", rotations);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function confirmWithAuthenticator(isLevelRaised: boolean) {
    const { t } = textsIn("en");
    answerStepUp({ method: "totp", passkey_available: false } as StepUpChallengeView, {
      ...VERIFIED,
      is_level_raised: isLevelRaised,
      rotation_ticket: isLevelRaised ? ROTATION_TICKET : null,
    });
    renderInLocale(<StepUpForm />);
    await userEvent.type(await screen.findByLabelText(t("mfa.stepUp.code")), "123456");
    await waitFor(() => expect(postsTo("/v1/auth/step-up/verify")).toHaveLength(1));
  }

  it("asks for a new session token once the level was raised, before the waiting requests run", async () => {
    await confirmWithAuthenticator(true);

    await waitFor(() => expect(settleStepUp).toHaveBeenCalledWith(true));
    expect(rotations).toHaveBeenCalledWith("/api/auth/session/rotate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ rotation_ticket: ROTATION_TICKET }),
    });
    expect(rotations.mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(settleStepUp).mock.invocationCallOrder[0] ?? 0,
    );
  });

  it("keeps the token when the session already had two factors", async () => {
    await confirmWithAuthenticator(false);

    await waitFor(() => expect(settleStepUp).toHaveBeenCalledWith(true));
    expect(rotations).not.toHaveBeenCalled();
  });
});
