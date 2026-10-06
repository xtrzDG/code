/**
 * What a platform admin's role lets them open (the API checks the same at
 * every request; the cabinet only hides what would be refused).
 */

import type { CurrentUserView, PlatformAdminPermission } from "@/api/types";

export function hasAdminPermission(
  me: Pick<CurrentUserView, "platform_admin_permissions">,
  permission: PlatformAdminPermission,
): boolean {
  return (me.platform_admin_permissions ?? []).includes(permission);
}

/** The permission each admin page needs, by its navigation key. */
const ADMIN_PAGE_PERMISSIONS = {
  admin: "view_clients",
  system: "view_operations",
  metrics: "view_metrics",
  security: "view_operations",
  team: "manage_admins",
  partners: "view_clients",
} as const satisfies Record<string, PlatformAdminPermission>;

export type AdminPageKey = keyof typeof ADMIN_PAGE_PERMISSIONS;

/** Whether the admin may open the page with this navigation key. */
export function canOpenAdminPage(
  me: Pick<CurrentUserView, "platform_admin_permissions">,
  page: AdminPageKey,
): boolean {
  return hasAdminPermission(me, ADMIN_PAGE_PERMISSIONS[page]);
}
