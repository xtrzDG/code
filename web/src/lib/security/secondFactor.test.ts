import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import {
  groupedKey,
  hasReason,
  isCompleteOneTimeCode,
  oneTimeCodeDigits,
  recoveryCodesFile,
  secondFactorProblem,
} from "./secondFactor";

function refusal(
  status: number,
  code: ApiError["code"],
  reasons: string[] = [],
): ApiError {
  return new ApiError({
    status,
    code,
    reasons: reasons.map((reason) => ({
      code: reason,
      message: "",
      details: [],
    })),
  });
}

describe("typed codes", () => {
  it("keeps six digits from any keyboard", () => {
    expect(oneTimeCodeDigits("12 34-56 78")).toBe("123456");
    expect(oneTimeCodeDigits("١٢٣٤٥٦")).toBe("123456");
    expect(isCompleteOneTimeCode("123456")).toBe(true);
    expect(isCompleteOneTimeCode("12345")).toBe(false);
  });

  it("shows the key in groups of four", () => {
    expect(groupedKey("ABCDEFGHIJKLMNOP")).toBe("ABCD EFGH IJKL MNOP");
    expect(groupedKey("")).toBe("");
  });

  it("writes the recovery codes one per line under a heading", () => {
    expect(
      recoveryCodesFile("Codes for me", ["aaaa-bbbb-cccc", "dddd-eeee-ffff"]),
    ).toBe("Codes for me\n\naaaa-bbbb-cccc\ndddd-eeee-ffff\n");
  });
});

describe("refused codes", () => {
  it("names a wrong code, an expired step and too many tries", () => {
    expect(
      secondFactorProblem(refusal(422, "validation_failed", ["wrong_code"])),
    ).toBe("mfa.errors.wrongCode");
    expect(secondFactorProblem(refusal(401, "authentication_required"))).toBe(
      "mfa.errors.expired",
    );
    expect(secondFactorProblem(refusal(429, "rate_limited"))).toBe(
      "mfa.errors.tooManyAttempts",
    );
    expect(secondFactorProblem(refusal(422, "validation_failed"))).toBe(
      "mfa.errors.wrongCode",
    );
    expect(
      secondFactorProblem(refusal(502, "external_service_error")),
    ).toBeNull();
  });

  it("finds a reason only on API errors", () => {
    expect(
      hasReason(
        refusal(403, "access_denied", ["mfa_required"]),
        "mfa_required",
      ),
    ).toBe(true);
    expect(hasReason(new Error("x"), "mfa_required")).toBe(false);
  });
});
