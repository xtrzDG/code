import { describe, expect, it } from "vitest";

import { AVATAR_TONE_COUNT, avatarTone, canReassign, menuOrder, teamMembers } from "./team";

const assignees = [
  { user_id: "user_staff_b", display_name: "Zurab", role: "staff", awaiting_count: 2 },
  { user_id: "user_owner", display_name: null, role: "owner", awaiting_count: 0 },
  { user_id: "user_staff_a", display_name: "Ana", role: "staff", awaiting_count: 1 },
] as const;

describe("the team in the inbox", () => {
  it("puts owners first, then names in order, and knows who I am", () => {
    const members = teamMembers(assignees, [{ user_id: "user_owner", email: "nino@example.com" }], "user_staff_b");
    expect(members.map((member) => member.userId)).toEqual(["user_owner", "user_staff_a", "user_staff_b"]);
    // Without a display name, the start of the e-mail address.
    expect(members[0]).toMatchObject({ name: "nino", role: "owner", awaitingCount: 0, isMe: false });
    expect(members.find((member) => member.isMe)?.name).toBe("Zurab");
  });

  it("lists me first in the assign menu", () => {
    const members = teamMembers(assignees, [], "user_staff_b");
    expect(menuOrder(members).map((member) => member.userId)).toEqual(["user_staff_b", "user_owner", "user_staff_a"]);
  });

  it("gives a person the same avatar tone everywhere", () => {
    expect(avatarTone("user_staff_a")).toBe(avatarTone("user_staff_a"));
    for (const { user_id: userId } of assignees) {
      expect(avatarTone(userId)).toBeGreaterThanOrEqual(0);
      expect(avatarTone(userId)).toBeLessThan(AVATAR_TONE_COUNT);
    }
  });
});

describe("who may change the assignment", () => {
  it("is an owner always, staff only for nobody's or their own conversation", () => {
    expect(canReassign(true, "user_other", "user_me")).toBe(true);
    expect(canReassign(false, null, "user_me")).toBe(true);
    expect(canReassign(false, "user_me", "user_me")).toBe(true);
    expect(canReassign(false, "user_other", "user_me")).toBe(false);
  });
});
