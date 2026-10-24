import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import { hasNewTelegramContact, isAlreadyContact, ownerChoices, ownerName, telegramContacts } from "./contacts";
import { generalQuestions, MAX_SUGGESTIONS, newTrySessionKey, suggestedQuestions, suggestionKey } from "./tryQuestions";

type Contact = Schema<"ManagerContactView">;

const contact = (channel: Contact["channel"], address: string): Contact => ({ name: "N", channel, address, language: "en" });

describe("the owner as a staff contact", () => {
  it("offers WhatsApp, SMS and e-mail from the sign-in details", () => {
    expect(ownerChoices({ phone_number: "+4915123456789", email: "a@b.de" })).toEqual([
      { channel: "whatsapp", address: "+4915123456789" },
      { channel: "sms", address: "+4915123456789" },
      { channel: "email", address: "a@b.de" },
    ]);
    expect(ownerChoices({ phone_number: null, email: "a@b.de" })).toEqual([{ channel: "email", address: "a@b.de" }]);
    expect(ownerChoices({})).toEqual([]);
  });

  it("greets the owner by name, else by the fallback", () => {
    expect(ownerName({ display_name: " Nino " }, "Owner")).toBe("Nino");
    expect(ownerName({ display_name: "  " }, "Owner")).toBe("Owner");
    expect(ownerName({ display_name: null }, "Owner")).toBe("Owner");
  });

  it("knows an address that already gets the handoffs", () => {
    const contacts = [contact("email", "A@B.de")];
    expect(isAlreadyContact(contacts, { channel: "email", address: "a@b.de" })).toBe(true);
    expect(isAlreadyContact(contacts, { channel: "sms", address: "a@b.de" })).toBe(false);
  });

  it("notices a Telegram chat linked after the link was made", () => {
    const before = [contact("telegram", "1"), contact("email", "a@b.de")];
    expect(telegramContacts(before)).toHaveLength(1);
    expect(hasNewTelegramContact(before, before)).toBe(false);
    expect(hasNewTelegramContact(before, [...before, contact("telegram", "2")])).toBe(true);
    expect(hasNewTelegramContact(before, [...before, contact("sms", "+491")])).toBe(false);
  });
});

describe("questions to try", () => {
  const faq: Schema<"StarterFaqView">[] = [
    { key: "a", question: "How do I book?", is_ready: true },
    { key: "b", question: " ", is_ready: false },
    { key: "c", question: "Can I pay by card?", is_ready: false },
    { key: "d", question: "Do you park cars?", is_ready: false },
  ];

  it("start with two niche questions, then the general ones", () => {
    const questions = suggestedQuestions(faq, true);
    expect(questions).toHaveLength(MAX_SUGGESTIONS);
    expect(questions.slice(0, 2)).toEqual([
      { kind: "niche", text: "How do I book?" },
      { kind: "niche", text: "Can I pay by card?" },
    ]);
    expect(questions[2]).toEqual({ kind: "general", key: "booking" });
  });

  it("leave out what was asked and bookings where nothing is booked", () => {
    expect(generalQuestions(false)).not.toContain("booking");
    const asked = new Set(["How do I book?", "hours"]);
    const questions = suggestedQuestions(faq, false, asked);
    expect(questions.map(suggestionKey)).toEqual(["Can I pay by card?", "Do you park cars?", "price", "person"]);
  });

  it("make distinct session keys the API accepts", () => {
    let seed = 0;
    const key = newTrySessionKey(() => ((seed += 0.37) % 1));
    expect(key).toMatch(/^tunnel[a-z0-9]{16}$/);
    expect(newTrySessionKey()).not.toBe(newTrySessionKey());
  });
});
