import { describe, expect, it } from "vitest";

import { contactLinks } from "./SupportContacts";

describe("contactLinks", () => {
  it("lists only the channels that are set, chats opening in a new tab", () => {
    const links = contactLinks({
      whatsapp_number: "+995555123456",
      whatsapp_url: "https://wa.me/995555123456",
      telegram_username: null,
      telegram_url: null,
      email: "help@example.com",
      email_url: "mailto:help@example.com",
    });
    expect(links.map((link) => [link.key, link.href, link.detail, link.external])).toEqual([
      ["whatsapp", "https://wa.me/995555123456", "+995555123456", true],
      ["email", "mailto:help@example.com", "help@example.com", false],
    ]);
  });

  it("shows the Telegram username with its @", () => {
    const links = contactLinks({ telegram_username: "workshop_help", telegram_url: "https://t.me/workshop_help" });
    expect(links.map((link) => link.detail)).toEqual(["@workshop_help"]);
  });

  it("has nothing before the contacts are loaded", () => {
    expect(contactLinks(undefined)).toEqual([]);
  });
});
