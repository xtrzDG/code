import { describe, expect, it } from "vitest";

import type { BusinessView, KnowledgeItemDetails, ProfileWizardView } from "@/api/types";
import { en } from "@/i18n/messages/en";
import { createTranslator } from "@/i18n/translate";

import { sectionSummary } from "./sectionSummaries";

const words = createTranslator("en", en);

const business = {
  name: "Mtsvane Ezo",
  languages: ["ka", "en"],
  manager_contacts: [
    { name: "Nino", channel: "email", address: "nino@example.com" },
    { name: "Nino", channel: "sms", address: "+995555000001" },
    { name: "David", channel: "telegram", address: "1" },
  ],
} as unknown as BusinessView;

const wizard = {
  niche: { name: "Restaurants and cafés", takes_bookings: true },
  profile: {
    address: { text: "Rustaveli 12, Tbilisi" },
    hours: [1, 2, 3, 4, 5].map((weekday) => ({ weekday, opens_at: 600, closes_at: 1380 })),
    booking_rules: { max_party_size: 12 },
    handoff_rules: ["A complaint"],
    forbidden: [],
  },
} as unknown as ProfileWizardView;

const items = [
  { kind: "menu_item", is_active: true, price_minor: 1800 },
  { kind: "menu_item", is_active: true, price_minor: null },
  { kind: "faq", is_active: true, price_minor: null },
] as unknown as KnowledgeItemDetails[];

describe("the cards of the business profile", () => {
  const input = { business, wizard, items };

  it("say what each section holds in a line", () => {
    expect(sectionSummary("business", input, words)).toBe("Mtsvane Ezo · Restaurants and cafés");
    expect(sectionSummary("place", input, words)).toBe("Rustaveli 12, Tbilisi · Georgian, English");
    expect(sectionSummary("offer", input, words)).toBe("2 items · 1 with a price");
    expect(sectionSummary("hours", input, words)).toBe("Mon–Fri 10:00–23:00 · up to 12 people per booking");
    expect(sectionSummary("people", input, words)).toBe("Nino and David");
    expect(sectionSummary("rules", input, words)).toBe("1 ready answer · 1 reason to call a person · 0 things never to promise");
  });

  it("say what is missing", () => {
    const empty = {
      business: { ...business, manager_contacts: [] },
      wizard: { ...wizard, niche: { ...wizard.niche, takes_bookings: false }, profile: { ...wizard.profile, address: null, hours: [] } } as unknown as ProfileWizardView,
      items: [],
    };
    expect(sectionSummary("place", empty, words)).toBe("No address yet · Georgian, English");
    expect(sectionSummary("offer", empty, words)).toBe("Nothing on offer yet");
    expect(sectionSummary("hours", empty, words)).toBe("Opening hours not set");
    expect(sectionSummary("people", empty, words)).toBe("No one gets the conversations yet");
  });

  it("wait for what a line needs", () => {
    const loading = { business, wizard: undefined, items: undefined };
    expect(sectionSummary("business", loading, words)).toBe("Mtsvane Ezo");
    for (const section of ["place", "offer", "hours", "rules"] as const) {
      expect(sectionSummary(section, loading, words)).toBeNull();
    }
  });
});
