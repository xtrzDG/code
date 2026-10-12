import { describe, expect, it } from "vitest";

import { platformAuditQuery, platformEntityKeys, SECURITY_EVENT_TONES, SECURITY_EVENTS, shortReference } from "./audit";

describe("platformAuditQuery", () => {
  it("asks for a page without a filter", () => {
    expect(platformAuditQuery("", { limit: 50 })).toEqual({ limit: "50" });
  });

  it("carries the cursor and the event", () => {
    expect(platformAuditQuery("otp_locked", { cursor: "abc", limit: 50 })).toEqual({
      limit: "50",
      cursor: "abc",
      security_event: "otp_locked",
    });
  });
});

describe("platformEntityKeys", () => {
  it("tries the platform's own name first, then the owners' one", () => {
    expect(platformEntityKeys("user_session")).toEqual(["adminAudit.entities.user_session", "settings.audit.entities.user_session"]);
    expect(platformEntityKeys("business_profile.contacts")).toEqual([
      "adminAudit.entities.business_profile_contacts",
      "settings.audit.entities.business_profile_contacts",
    ]);
  });
});

describe("shortReference", () => {
  it("keeps a digest recognisable but short", () => {
    expect(shortReference("dest_0123456789abcdef0123456789abcdef")).toBe("dest_01234567");
  });

  it("drops an id's prefix", () => {
    expect(shortReference("user_af961b93-ec8d-4c4c")).toBe("af961b93");
    expect(shortReference("plain")).toBe("plain");
  });
});

describe("security events", () => {
  it("has a tone for every event of the filter", () => {
    expect(SECURITY_EVENTS.map((event) => SECURITY_EVENT_TONES[event])).toEqual(["warning", "danger", "danger", "neutral", "accent"]);
  });
});
