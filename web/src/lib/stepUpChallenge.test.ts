import { describe, expect, it } from "vitest";

import { isStepUpChallenge } from "./stepUpChallenge";

describe("the API's 'confirm it is you' refusal", () => {
  it("is a 401 that names insufficient_user_authentication", () => {
    const challenge = new Headers({
      "www-authenticate": 'Bearer error="insufficient_user_authentication", max_age=600',
    });
    expect(isStepUpChallenge(401, challenge)).toBe(true);
  });

  it("is not an ended session nor another status", () => {
    expect(isStepUpChallenge(401, new Headers())).toBe(false);
    expect(isStepUpChallenge(401, new Headers({ "www-authenticate": 'Bearer error="invalid_token"' }))).toBe(false);
    expect(
      isStepUpChallenge(403, new Headers({ "www-authenticate": 'Bearer error="insufficient_user_authentication"' })),
    ).toBe(false);
  });
});
