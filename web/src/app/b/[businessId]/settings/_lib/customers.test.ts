import { describe, expect, it } from "vitest";

import { contactSearchParam, erasureConfirmation, markErased, type ContactSummary } from "./customers";

describe("customer data requests", () => {
  const contact = (overrides: Partial<ContactSummary> = {}): ContactSummary => ({
    id: "contact_a",
    name: "Ana",
    phone_number: "+995599112233",
    is_phone_verified: true,
    language: "ka",
    channels: ["telegram"],
    conversation_count: 2,
    booking_count: 1,
    lead_count: 0,
    first_seen_at: 1,
    last_activity_at: 10,
    erased_at: null,
    ...overrides,
  });

  it("asks to type the name, else the phone, else the id", () => {
    expect(erasureConfirmation({ id: "contact_a", name: " Ana ", phone_number: "+1" })).toBe("Ana");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: "+995599112233" })).toBe("+995599112233");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: null })).toBe("contact_a");
  });

  it("shows an erased customer without personal data", () => {
    expect(markErased(contact(), 99)).toEqual(
      contact({ name: null, phone_number: null, is_phone_verified: false, language: null, erased_at: 99 }),
    );
  });

  it("sends a trimmed search, or none", () => {
    expect(contactSearchParam("  599 11 ")).toBe("599 11");
    expect(contactSearchParam("   ")).toBeUndefined();
    expect(contactSearchParam("x".repeat(150))).toHaveLength(100);
  });
});
