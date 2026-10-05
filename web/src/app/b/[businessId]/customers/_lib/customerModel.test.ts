import { describe, expect, it } from "vitest";

import {
  cardOf,
  changedCard,
  cleanTag,
  customerName,
  erasureConfirmation,
  hasTag,
  markErased,
  MAX_TAGS_PER_CUSTOMER,
  shownPhone,
  tagProblem,
  tagSuggestions,
  withCard,
  type CustomerCard,
  type CustomerDetail,
  type CustomerSummary,
} from "./customerModel";

const contact = (overrides: Partial<CustomerSummary> = {}): CustomerSummary => ({
  id: "contact_a",
  name: "Nino Beridze",
  phone_number: "+995599112233",
  masked_phone_number: null,
  is_phone_masked: false,
  is_phone_verified: true,
  language: "ka",
  channels: ["telegram"],
  conversation_count: 2,
  booking_count: 4,
  lead_count: 0,
  first_seen_at: 1,
  last_activity_at: 10,
  erased_at: null,
  tags: ["regular"],
  is_vip: true,
  is_blocked: false,
  ...overrides,
});

const card = (overrides: Partial<CustomerCard> = {}): CustomerCard => ({
  contact_id: "contact_a",
  tags: ["regular", "Terrace"],
  is_vip: false,
  is_blocked: false,
  blocked_at: null,
  known_tags: [],
  ...overrides,
});

describe("a customer's name and phone", () => {
  it("shows the full phone to whoever may see it, else the masked one", () => {
    expect(shownPhone(contact())).toEqual({ text: "+995 599 11 22 33", isMasked: false });
    expect(shownPhone(contact({ phone_number: null, masked_phone_number: "+995 ••• ••• •33", is_phone_masked: true }))).toEqual({
      text: "+995 ••• ••• •33",
      isMasked: true,
    });
    expect(shownPhone(contact({ phone_number: null }))).toBeNull();
  });

  it("calls them by name, else by phone, else unnamed", () => {
    expect(customerName(contact({ name: "  Ana " }), "?")).toBe("Ana");
    expect(customerName(contact({ name: null, phone_number: null, masked_phone_number: "+995 ••• •33" }), "?")).toBe("+995 ••• •33");
    expect(customerName(contact({ name: null, phone_number: null }), "No name")).toBe("No name");
  });
});

describe("erasing a customer's data", () => {
  it("asks to type the name, else the phone, else the id", () => {
    expect(erasureConfirmation({ id: "contact_a", name: " Ana ", phone_number: "+1" })).toBe("Ana");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: "+995599112233" })).toBe("+995599112233");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: null })).toBe("contact_a");
  });

  it("leaves nothing personal and no card", () => {
    const erased = markErased(contact(), 99);
    expect(erased).toMatchObject({ name: null, phone_number: null, tags: [], is_vip: false, is_blocked: false, erased_at: 99 });
    expect(erased.booking_count).toBe(4);
  });
});

describe("tags on a card", () => {
  it("cleans what is typed", () => {
    expect(cleanTag("  big \n  table ")).toBe("big table");
    expect(cleanTag("\u0007")).toBe("");
  });

  it("compares without case", () => {
    expect(hasTag(["Regular"], "REGULAR")).toBe(true);
    expect(hasTag(["Regular"], "vip")).toBe(false);
  });

  it("says why a tag cannot be added", () => {
    expect(tagProblem("  ", [])).toBe("empty");
    expect(tagProblem("x".repeat(33), [])).toBe("tooLong");
    expect(tagProblem("regular", ["Regular"])).toBe("duplicate");
    expect(tagProblem("new", Array.from({ length: MAX_TAGS_PER_CUSTOMER }, (_, index) => `t${index}`))).toBe("tooMany");
    expect(tagProblem("terrace", ["regular"])).toBeNull();
  });

  it("suggests the business's tags the card lacks, starting ones first", () => {
    const known = ["regular", "allergy", "wholesale", "terrace", "large group"];
    expect(tagSuggestions(known, ["Regular"], "")).toEqual(["allergy", "wholesale", "terrace", "large group"]);
    expect(tagSuggestions(known, [], "AL")).toEqual(["allergy", "wholesale"]);
    expect(tagSuggestions(known, [], "zzz")).toEqual([]);
  });

  it("applies a change the way the API will", () => {
    expect(changedCard(card(), { add_tags: ["VIP guest", "regular"], remove_tags: ["TERRACE"], is_vip: true })).toEqual(
      card({ tags: ["regular", "VIP guest"], is_vip: true }),
    );
    expect(changedCard(card(), {})).toEqual(card());
  });

  it("reads and writes the card of a customer page", () => {
    const detail: CustomerDetail = { contact: contact(), visit_count: 4, standing: "regular", blocked_at: null };
    expect(cardOf(detail, ["a"])).toEqual(card({ tags: ["regular"], is_vip: true, known_tags: ["a"] }));
    const blocked = withCard(detail, card({ is_blocked: true, blocked_at: 5, tags: [] }));
    expect(blocked.blocked_at).toBe(5);
    expect(blocked.contact).toMatchObject({ is_blocked: true, tags: [], is_vip: false });
  });
});
