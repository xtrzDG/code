/** Pure helpers of the Settings page's Team tab: members, their roles and invitations. */

import type { RequestBody, Schema } from "@/api/types";

export type BusinessMember = Schema<"BusinessMemberView">;

/** The name to show for a member: display name, else phone, else e-mail. */
export function memberLabel(member: Pick<BusinessMember, "display_name" | "phone_number" | "email">): string {
  return member.display_name || member.phone_number || member.email || "";
}

/** Up to two initials of a member's display name ("Nino Beridze" -> "NB"), or null without a name. */
export function memberInitials(member: Pick<BusinessMember, "display_name">): string | null {
  const parts = (member.display_name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return null;
  }
  // Georgian has no capital letters in normal text (Mtavruli is for headings).
  const capital = (letter: string) => (/[\u10A0-\u10FF]/.test(letter) ? letter : letter.toLocaleUpperCase());
  return parts
    .slice(0, 2)
    .map((part) => capital([...part][0] ?? ""))
    .join("");
}

/** Owners first, then by name. */
export function sortMembers(members: readonly BusinessMember[]): BusinessMember[] {
  return [...members].sort((left, right) => {
    if (left.role !== right.role) {
      return left.role === "owner" ? -1 : 1;
    }
    return memberLabel(left).localeCompare(memberLabel(right));
  });
}

/** A business always keeps one owner: the last owner can be neither removed nor made staff. */
export function canRemoveMember(member: BusinessMember, members: readonly BusinessMember[]): boolean {
  if (member.role !== "owner") {
    return true;
  }
  return members.filter((item) => item.role === "owner").length > 1;
}

export type MemberRole = BusinessMember["role"];

/** The name of each member role. */
export const ROLE_NAMES: Record<MemberRole, "settings.roles.owner" | "settings.roles.staff"> = {
  owner: "settings.roles.owner",
  staff: "settings.roles.staff",
};

/** The roles a member may get now: staff only while another owner remains. */
export function allowedRoles(member: BusinessMember, members: readonly BusinessMember[]): MemberRole[] {
  return canRemoveMember(member, members) ? ["owner", "staff"] : ["owner"];
}

export type InviteMethod = "phone" | "email";

export interface InviteForm {
  method: InviteMethod;
  phone: string;
  countryHint: string;
  email: string;
  displayName: string;
  role: MemberRole;
}

export type InviteBody = RequestBody<"/v1/businesses/{business_id}/members", "post">;
export type InviteError = "required" | "email";

/** A loose e-mail shape check; the API validates for real. */
export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function buildInviteBody(
  form: InviteForm,
): { ok: true; body: InviteBody } | { ok: false; errors: Partial<Record<"phone" | "email", InviteError>> } {
  const displayName = form.displayName.trim();
  const named = { ...(displayName ? { display_name: displayName } : {}), role: form.role };
  if (form.method === "phone") {
    const phone = form.phone.trim();
    if (phone === "") {
      return { ok: false, errors: { phone: "required" } };
    }
    const hint = form.countryHint.trim().toUpperCase();
    return {
      ok: true,
      body: { phone_number: phone, ...(/^[A-Z]{2}$/.test(hint) ? { country_hint: hint } : {}), ...named },
    };
  }
  const email = form.email.trim();
  if (email === "") {
    return { ok: false, errors: { email: "required" } };
  }
  if (!EMAIL.test(email)) {
    return { ok: false, errors: { email: "email" } };
  }
  return { ok: true, body: { email, ...named } };
}
