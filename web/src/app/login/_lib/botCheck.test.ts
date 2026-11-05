import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import { findBotCheckSiteKey, turnstileLanguage, turnstileTheme } from "./botCheck";

function refusal(status: number, reasons: ApiError["reasons"]): ApiError {
  return new ApiError({ status, code: status === 403 ? "access_denied" : "rate_limited", reasons });
}

const CHALLENGE = { code: "challenge_required", message: "Confirm that you are not a robot.", details: ["0x4AAAAAAABkMYinukE8nzY"] };

describe("findBotCheckSiteKey", () => {
  it("reads the site key of a challenge_required refusal", () => {
    expect(findBotCheckSiteKey(refusal(403, [CHALLENGE]))).toBe("0x4AAAAAAABkMYinukE8nzY");
  });

  it("ignores other refusals, other statuses and malformed keys", () => {
    expect(findBotCheckSiteKey(refusal(403, []))).toBeNull();
    expect(findBotCheckSiteKey(refusal(403, [{ ...CHALLENGE, code: "dpa" }]))).toBeNull();
    expect(findBotCheckSiteKey(refusal(429, [CHALLENGE]))).toBeNull();
    expect(findBotCheckSiteKey(refusal(403, [{ ...CHALLENGE, details: [] }]))).toBeNull();
    expect(findBotCheckSiteKey(refusal(403, [{ ...CHALLENGE, details: ["<script>"] }]))).toBeNull();
  });
});

describe("turnstile appearance", () => {
  it("follows the cabinet theme and language", () => {
    expect(turnstileTheme("dark")).toBe("dark");
    expect(turnstileTheme("light")).toBe("light");
    expect(turnstileTheme("system")).toBe("auto");
    expect(turnstileLanguage("ru")).toBe("ru");
    expect(turnstileLanguage("ka")).toBe("en");
  });
});
