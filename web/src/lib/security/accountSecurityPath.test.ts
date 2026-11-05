import { describe, expect, it } from "vitest";

import { ACCOUNT_SECURITY_PATH, isProtectedPath, isSecurityReason, securityPath } from "../navigation";

describe("Account → Security", () => {
  it("opens plainly, or with why and where to go back", () => {
    expect(securityPath()).toBe(ACCOUNT_SECURITY_PATH);
    expect(securityPath({ reason: "admin", next: "/admin" })).toBe("/account/security?reason=admin&next=%2Fadmin");
    expect(securityPath({ reason: "business", next: "/b/biz_1/inbox?view=mine" })).toBe(
      "/account/security?reason=business&next=%2Fb%2Fbiz_1%2Finbox%3Fview%3Dmine",
    );
  });

  it("never sends people back to another site", () => {
    expect(securityPath({ next: "https://evil.example/" })).toBe(ACCOUNT_SECURITY_PATH);
    expect(securityPath({ next: "//evil.example" })).toBe(ACCOUNT_SECURITY_PATH);
    expect(securityPath({ reason: "admin", next: null })).toBe("/account/security?reason=admin");
  });

  it("knows its reasons and needs a session", () => {
    expect(isSecurityReason("admin")).toBe(true);
    expect(isSecurityReason("business")).toBe(true);
    expect(isSecurityReason("other")).toBe(false);
    expect(isSecurityReason(null)).toBe(false);
    expect(isProtectedPath(ACCOUNT_SECURITY_PATH)).toBe(true);
  });
});
