import { describe, expect, it, vi } from "vitest";

import type { StepUpChallengeView } from "@/api/types";

import { createStepUpAsker } from "./stepUpAsker";

const TOTP: StepUpChallengeView = { method: "totp", login_code: null };

function loginCode(challengeId: string): StepUpChallengeView {
  return {
    method: "login_code",
    login_code: {
      challenge_id: challengeId,
      login_method: "email",
      delivery_channel: "email",
      masked_destination: "o***@example.com",
      expires_in_seconds: 300,
    },
  } as StepUpChallengeView;
}

describe("asking how to confirm", () => {
  it("shares one ask between everyone waiting", async () => {
    const request = vi.fn(async () => TOTP);
    const asker = createStepUpAsker(request);

    const [first, second] = await Promise.all([asker.ask(), asker.ask()]);

    expect(first).toBe(TOTP);
    expect(second).toBe(TOTP);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("offers a login code sent moments ago again instead of sending another", async () => {
    let now = 1_000_000;
    const request = vi.fn().mockResolvedValueOnce(loginCode("challenge_1")).mockResolvedValueOnce(loginCode("challenge_2"));
    const asker = createStepUpAsker(request, () => now);

    const sent = await asker.ask();
    now += 60_000;
    const again = await asker.ask();
    // Shortly before it expires (five minutes), a new code is sent.
    now += 215_000;
    const renewed = await asker.ask();

    expect(again).toBe(sent);
    expect(renewed.login_code?.challenge_id).toBe("challenge_2");
    expect(request).toHaveBeenCalledTimes(2);
  });

  it("sends a new code on request and after the code was used", async () => {
    const request = vi
      .fn()
      .mockResolvedValueOnce(loginCode("challenge_1"))
      .mockResolvedValueOnce(loginCode("challenge_2"))
      .mockResolvedValueOnce(loginCode("challenge_3"));
    const asker = createStepUpAsker(request);

    await asker.ask();
    const fresh = await asker.ask({ fresh: true });
    asker.forget();
    const afterUse = await asker.ask();

    expect(fresh.login_code?.challenge_id).toBe("challenge_2");
    expect(afterUse.login_code?.challenge_id).toBe("challenge_3");
  });

  it("asks again after a failed ask, and never keeps an authenticator answer", async () => {
    const request = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue(TOTP);
    const asker = createStepUpAsker(request);

    await expect(asker.ask()).rejects.toThrow("offline");
    await asker.ask();
    await asker.ask();

    expect(request).toHaveBeenCalledTimes(3);
  });
});
