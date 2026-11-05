import { describe, expect, it } from "vitest";

import { businessIdOfLinkToken, linkTargetPath, type StaffLinkView } from "./notificationLinks";

const BUSINESS_UUID = "c48682e1-394e-45ea-8ea8-a01b6d57cf40";

/** A token of `version` whose signature has `signatureBytes` bytes (16 in version 2, 12 in version 1). */
function token(version = 2, extraBytes = 0, signatureBytes = version === 1 ? 12 : 16): string {
  const bytes = new Uint8Array(38 + signatureBytes + extraBytes);
  bytes[0] = version;
  const uuid = BUSINESS_UUID.replace(/-/g, "");
  for (let index = 0; index < 16; index += 1) {
    bytes[1 + index] = parseInt(uuid.slice(index * 2, index * 2 + 2), 16);
  }
  bytes.fill(7, 17);
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

const view = (patch: Partial<StaffLinkView>): StaffLinkView => ({
  business_id: `business_${BUSINESS_UUID}`,
  target: "notifications",
  expires_at: 1,
  is_expired: false,
  ...patch,
});

describe("notification links", () => {
  it("name the business they were signed for", () => {
    expect(token()).toHaveLength(72);
    expect(businessIdOfLinkToken(token())).toBe(`business_${BUSINESS_UUID}`);
  });

  it("still read the links of version 1, sent before the longer signature", () => {
    expect(token(1)).toHaveLength(67);
    expect(businessIdOfLinkToken(token(1))).toBe(`business_${BUSINESS_UUID}`);
  });

  it("refuse what is not a token", () => {
    expect(businessIdOfLinkToken("short")).toBeNull();
    expect(businessIdOfLinkToken(token(2, 3))).toBeNull();
    expect(businessIdOfLinkToken(token(1, 3))).toBeNull();
    // A version's byte with the other version's signature length, or an unknown version.
    expect(businessIdOfLinkToken(token(2, 0, 12))).toBeNull();
    expect(businessIdOfLinkToken(token(1, 0, 16))).toBeNull();
    expect(businessIdOfLinkToken(token(3))).toBeNull();
    expect(businessIdOfLinkToken(`${token().slice(0, 60)}!@#$%^&`)).toBeNull();
    expect(businessIdOfLinkToken("A".repeat(65))).toBeNull();
  });

  it("open the page of their target", () => {
    const business = `/b/business_${BUSINESS_UUID}`;
    expect(linkTargetPath(view({ target: "conversation", conversation_id: "conversation_1" }))).toBe(
      `${business}/inbox/conversation_1`,
    );
    expect(linkTargetPath(view({ target: "conversation" }))).toBe(`${business}/inbox`);
    expect(linkTargetPath(view({ target: "lead", lead_id: "lead_1" }))).toBe(`${business}/inbox?view=requests`);
    expect(linkTargetPath(view({ target: "lead", lead_id: "lead_1", conversation_id: "conversation_2" }))).toBe(
      `${business}/inbox/conversation_2`,
    );
    expect(linkTargetPath(view({ target: "booking", booking_date: "2026-10-10" }))).toBe(
      `${business}/bookings?range=custom&from=2026-10-10&to=2026-10-10`,
    );
    expect(linkTargetPath(view({ target: "booking" }))).toBe(`${business}/bookings`);
    expect(linkTargetPath(view({}))).toBe(`${business}/settings/notifications`);
    expect(linkTargetPath(view({ target: "report", value_report_id: "value_report_1" }))).toBe(
      `${business}/overview/reports?report=value_report_1`,
    );
    expect(linkTargetPath(view({ target: "report" }))).toBe(`${business}/overview/reports`);
    // A milestone's celebration and the activation reminders.
    expect(linkTargetPath(view({ target: "overview" }))).toBe(`${business}/overview`);
    expect(linkTargetPath(view({ target: "setup" }))).toBe(`${business}/setup`);
    expect(linkTargetPath(view({ target: "channels" }))).toBe(`${business}/assistant/channels`);
    expect(linkTargetPath(view({ target: "share" }))).toBe(`${business}/assistant/channels#share`);
    expect(linkTargetPath(view({ target: "billing" }))).toBe(`${business}/settings/billing#setup-options`);
    expect(linkTargetPath(view({ target: "privacy" }))).toBe(`${business}/settings/privacy`);
    expect(linkTargetPath(view({ target: "integrations" }))).toBe(`${business}/settings/integrations`);
  });
});
