/**
 * The platform admin team as the Team page shows it: the roles in order,
 * their texts, and what may be changed without leaving the team without
 * a super admin (the API refuses the same with 409).
 */

import type { PlatformAdminRole, PlatformAdminView } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export const ADMIN_ROLES: readonly PlatformAdminRole[] = ["super", "support_readonly", "billing"];

export const ROLE_LABELS: Record<PlatformAdminRole, MessageKey> = {
  super: "adminTeam.roles.super",
  support_readonly: "adminTeam.roles.support_readonly",
  billing: "adminTeam.roles.billing",
};

export const ROLE_HINTS: Record<PlatformAdminRole, MessageKey> = {
  super: "adminTeam.roleHints.super",
  support_readonly: "adminTeam.roleHints.support_readonly",
  billing: "adminTeam.roleHints.billing",
};

/** The only super admin cannot lose the role or leave the team. */
export function isLastSuper(admin: PlatformAdminView, team: readonly PlatformAdminView[]): boolean {
  return admin.role === "super" && team.filter((member) => member.role === "super").length === 1;
}

/** How the person signs in: their phone number or e-mail. */
export function adminDestination(admin: PlatformAdminView): string {
  return admin.phone_number ?? admin.email ?? "";
}

export type AddAdminBy = "phone" | "email";

/** The body of POST /v1/admin/team: one destination, never both. */
export function addAdminBody(by: AddAdminBy, value: string, role: PlatformAdminRole) {
  const destination = value.trim();
  return by === "phone" ? { phone_number: destination, role } : { email: destination, role };
}
