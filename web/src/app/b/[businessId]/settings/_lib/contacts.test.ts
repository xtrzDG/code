import { describe, expect, it } from "vitest";

import { applyContactChange, contactFromForm, contactsToInput, validateContact } from "./contacts";

describe("notification contacts", () => {
  const existing = [{ name: "Nino", channel: "email" as const, address: "nino@example.com", language: "ka" }];

  it("checks names and addresses per channel", () => {
    expect(validateContact({ name: "", channel: "email", address: "", language: "ka" }, [])).toEqual({
      name: "required",
      address: "required",
    });
    expect(validateContact({ name: "Levan", channel: "email", address: "levan", language: "ka" }, [])).toEqual({
      address: "email",
    });
    expect(validateContact({ name: "Levan", channel: "telegram", address: "@levan", language: "ka" }, [])).toEqual({
      address: "chatId",
    });
    expect(validateContact({ name: "Levan", channel: "telegram", address: "-100123", language: "ka" }, [])).toEqual({});
    expect(validateContact({ name: "Levan", channel: "whatsapp", address: "599 11 22 33", language: "ka" }, [])).toEqual({});
  });

  it("refuses the same address twice", () => {
    expect(validateContact({ name: "N", channel: "email", address: "NINO@example.com", language: "ka" }, existing)).toEqual({
      address: "duplicate",
    });
  });

  it("maps contacts to the PATCH input", () => {
    expect(contactsToInput(existing)).toEqual(existing);
    expect(contactFromForm({ name: " Levan ", channel: "sms", address: " 599 ", language: "ru" })).toEqual({
      name: "Levan",
      channel: "sms",
      address: "599",
      language: "ru",
    });
  });
});

describe("applyContactChange", () => {
  const emailA = { name: "Anna", channel: "email" as const, address: "anna@example.com", language: "en" };
  const emailB = { name: "Beka", channel: "email" as const, address: "beka@example.com", language: "ka" };
  // Linked by the manager through the platform bot after the page loaded.
  const telegram = { name: "Levan", channel: "telegram" as const, address: "777000111", language: "ka" };

  it("keeps contacts added on the server since the page loaded", () => {
    expect(applyContactChange([emailA, telegram], { kind: "add", contact: emailB })).toEqual([emailA, telegram, emailB]);
  });

  it("edits and removes by channel and address, wherever the contact is now", () => {
    const fresh = [telegram, emailA];
    const original = { channel: "email" as const, address: "anna@example.com" };
    expect(applyContactChange(fresh, { kind: "remove", original })).toEqual([telegram]);
    expect(applyContactChange(fresh, { kind: "edit", original, contact: { ...emailA, name: "Anna K." } })).toEqual([
      telegram,
      { ...emailA, name: "Anna K." },
    ]);
  });
});
