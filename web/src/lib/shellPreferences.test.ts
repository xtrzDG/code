import { describe, expect, it } from "vitest";

import { SIDEBAR_COOKIE, readSidebarState, sidebarCookie } from "./shellPreferences";

describe("sidebar preference", () => {
  it("reads only 'collapsed' as collapsed", () => {
    expect(readSidebarState("collapsed")).toBe("collapsed");
    expect(readSidebarState("expanded")).toBe("expanded");
    expect(readSidebarState("anything")).toBe("expanded");
    expect(readSidebarState(undefined)).toBe("expanded");
    expect(readSidebarState(null)).toBe("expanded");
  });

  it("keeps the choice for a year on the whole site", () => {
    expect(sidebarCookie("collapsed")).toBe(`${SIDEBAR_COOKIE}=collapsed; Path=/; Max-Age=31536000; SameSite=Lax`);
  });
});
