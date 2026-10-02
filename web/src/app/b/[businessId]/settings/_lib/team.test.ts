import { describe, expect, it } from "vitest";

import { allowedRoles, buildInviteBody, canRemoveMember, memberInitials, memberLabel, sortMembers } from "./team";
import { member } from "./settingsFixtures";

describe("team", () => {
  const owner = member({ user_id: "u1", role: "owner", display_name: "Dato" });
  const staff = member({ user_id: "u2", phone_number: "+995555654321" });
  const emailOnly = member({ user_id: "u3", email: "giorgi@example.com" });

  it("labels members by name, phone or e-mail", () => {
    expect(memberLabel(owner)).toBe("Dato");
    expect(memberLabel(staff)).toBe("+995555654321");
    expect(memberLabel(emailOnly)).toBe("giorgi@example.com");
  });

  it("makes initials from display names only", () => {
    expect(memberInitials({ display_name: "Nino Beridze" })).toBe("NB");
    expect(memberInitials({ display_name: "ნინო" })).toBe("ნ");
    expect(memberInitials({ display_name: "  " })).toBeNull();
    expect(memberInitials({ display_name: null })).toBeNull();
  });

  it("lists owners first", () => {
    expect(sortMembers([staff, owner, emailOnly]).map((item) => item.user_id)).toEqual(["u1", "u2", "u3"]);
  });

  it("keeps the last owner", () => {
    expect(canRemoveMember(owner, [owner, staff])).toBe(false);
    expect(canRemoveMember(owner, [owner, member({ user_id: "u4", role: "owner" })])).toBe(true);
    expect(canRemoveMember(staff, [owner, staff])).toBe(true);
    expect(allowedRoles(owner, [owner, staff])).toEqual(["owner"]);
    expect(allowedRoles(owner, [owner, member({ user_id: "u4", role: "owner" })])).toEqual(["owner", "staff"]);
    expect(allowedRoles(staff, [owner, staff])).toEqual(["owner", "staff"]);
  });

  it("builds invitations by phone or e-mail with a role", () => {
    const base = { method: "phone" as const, phone: "", countryHint: "ge", email: "", displayName: "", role: "staff" as const };
    expect(buildInviteBody(base)).toEqual({ ok: false, errors: { phone: "required" } });
    expect(buildInviteBody({ ...base, phone: "555 65 43 21", displayName: " Nino " })).toEqual({
      ok: true,
      body: { phone_number: "555 65 43 21", country_hint: "GE", display_name: "Nino", role: "staff" },
    });
    expect(buildInviteBody({ ...base, method: "email", email: "nino@" })).toEqual({ ok: false, errors: { email: "email" } });
    expect(buildInviteBody({ ...base, method: "email", email: " nino@example.com ", role: "owner" })).toEqual({
      ok: true,
      body: { email: "nino@example.com", role: "owner" },
    });
  });
});
