import { describe, expect, it } from "vitest";

import { canOpenAdminPage, hasAdminPermission } from "./adminPermissions";

const billing = { platform_admin_permissions: ["view_clients", "view_metrics"] as const };
const support = {
  platform_admin_permissions: ["view_clients", "open_client_cabinet", "view_operations"] as const,
};

describe("admin permissions", () => {
  it("reads the role's permissions from /v1/me", () => {
    expect(hasAdminPermission({ platform_admin_permissions: [...billing.platform_admin_permissions] }, "view_metrics")).toBe(true);
    expect(hasAdminPermission({ platform_admin_permissions: [...billing.platform_admin_permissions] }, "open_client_cabinet")).toBe(false);
    expect(hasAdminPermission({}, "view_clients")).toBe(false);
  });

  it("opens only the pages of the role", () => {
    const me = { platform_admin_permissions: [...support.platform_admin_permissions] };
    expect(canOpenAdminPage(me, "admin")).toBe(true);
    expect(canOpenAdminPage(me, "system")).toBe(true);
    expect(canOpenAdminPage(me, "metrics")).toBe(false);
    expect(canOpenAdminPage(me, "team")).toBe(false);
  });
});
