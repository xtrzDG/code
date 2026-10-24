import { describe, expect, it } from "vitest";

import type { PlatformAdminView } from "@/api/types";

import { addAdminBody, adminDestination, isLastSuper } from "./team";

function admin(id: string, role: PlatformAdminView["role"], email?: string): PlatformAdminView {
  return { id, login_method: "email", email, role, created_at: 1, is_you: false };
}

describe("admin team", () => {
  it("keeps one super admin on the team", () => {
    const boss = admin("a", "super", "boss@example.com");
    const helper = admin("b", "billing");
    expect(isLastSuper(boss, [boss, helper])).toBe(true);
    expect(isLastSuper(boss, [boss, admin("c", "super")])).toBe(false);
    expect(isLastSuper(helper, [boss, helper])).toBe(false);
  });

  it("names how the person signs in", () => {
    expect(adminDestination(admin("a", "super", "boss@example.com"))).toBe("boss@example.com");
    expect(adminDestination({ ...admin("b", "billing"), login_method: "phone", phone_number: "+995555123456" })).toBe(
      "+995555123456",
    );
  });

  it("sends one destination", () => {
    expect(addAdminBody("email", " ops@example.com ", "billing")).toEqual({ email: "ops@example.com", role: "billing" });
    expect(addAdminBody("phone", "+995 555 12 34 56", "super")).toEqual({ phone_number: "+995 555 12 34 56", role: "super" });
  });
});
