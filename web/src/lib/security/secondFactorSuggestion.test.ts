import { describe, expect, it } from "vitest";

import { HOME_PATH } from "@/lib/navigation";

import { afterSignInPath, PROTECT_ACCOUNT_PATH, suggestionNext } from "./secondFactorSuggestion";

describe("after a sign-in", () => {
  it("goes straight on when nothing is suggested", () => {
    expect(afterSignInPath("/b/biz_1/overview", false)).toBe("/b/biz_1/overview");
  });

  it("shows an owner the suggestion first, keeping where they were going", () => {
    expect(afterSignInPath("/b/biz_1/overview", true)).toBe(
      `${PROTECT_ACCOUNT_PATH}?next=%2Fb%2Fbiz_1%2Foverview`,
    );
    expect(afterSignInPath("/", true)).toBe(`${PROTECT_ACCOUNT_PATH}?next=%2F`);
  });

  it("never stands between the owner and Account → Security", () => {
    expect(afterSignInPath("/account/security", true)).toBe("/account/security");
    expect(afterSignInPath("/account/security?reason=business", true)).toBe("/account/security?reason=business");
    expect(afterSignInPath(`${PROTECT_ACCOUNT_PATH}?next=%2F`, true)).toBe(`${PROTECT_ACCOUNT_PATH}?next=%2F`);
  });
});

describe("the suggestion's way on", () => {
  it("keeps a path on this site", () => {
    expect(suggestionNext("/b/biz_1/inbox")).toBe("/b/biz_1/inbox");
  });

  it("refuses other sites, itself and nothing, going home instead", () => {
    expect(suggestionNext("https://evil.example/")).toBe(HOME_PATH);
    expect(suggestionNext("//evil.example")).toBe(HOME_PATH);
    expect(suggestionNext(PROTECT_ACCOUNT_PATH)).toBe(HOME_PATH);
    expect(suggestionNext(undefined)).toBe(HOME_PATH);
  });
});
