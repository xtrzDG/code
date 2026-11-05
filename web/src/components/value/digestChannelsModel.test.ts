import { describe, expect, it } from "vitest";

import {
  canTurnOn,
  normalizeWhatsAppNumber,
  telegramChatFor,
  whatsappNumberFor,
  withChannel,
  type DigestPreferencesView,
} from "./digestChannelsModel";

function preferences(overrides: Partial<DigestPreferencesView> = {}): DigestPreferencesView {
  return {
    business_id: "biz_1",
    is_daily_digest_on: false,
    is_weekly_digest_on: true,
    is_monthly_report_on: true,
    channels: ["email", "push"],
    email: "owner@example.com",
    is_email_ready: true,
    device_count: 0,
    telegram_chat: null,
    telegram_chats: [],
    is_telegram_ready: true,
    whatsapp_number: null,
    suggested_whatsapp_number: null,
    is_whatsapp_ready: true,
    ...overrides,
  };
}

const chats = [
  { address: "1001", name: "Nino", username: "nino" },
  { address: "1002", name: "Giorgi", username: null },
];

describe("withChannel", () => {
  it("switches one channel, keeping the API's order and no repeats", () => {
    expect(withChannel(["push", "email"], "whatsapp", true)).toEqual(["email", "push", "whatsapp"]);
    expect(withChannel(["email", "push"], "email", true)).toEqual(["email", "push"]);
    expect(withChannel(["email", "push", "telegram"], "push", false)).toEqual(["email", "telegram"]);
  });
});

describe("canTurnOn", () => {
  it("offers e-mail only with an address the platform can send to", () => {
    expect(canTurnOn(preferences(), "email")).toBe(true);
    expect(canTurnOn(preferences({ email: null }), "email")).toBe(false);
    expect(canTurnOn(preferences({ is_email_ready: false }), "email")).toBe(false);
    expect(canTurnOn(preferences(), "push")).toBe(true);
  });

  it("offers Telegram with the platform bot and a linked chat, WhatsApp with the template", () => {
    expect(canTurnOn(preferences(), "telegram")).toBe(false);
    expect(canTurnOn(preferences({ telegram_chats: chats }), "telegram")).toBe(true);
    expect(canTurnOn(preferences({ telegram_chats: chats, is_telegram_ready: false }), "telegram")).toBe(false);
    expect(canTurnOn(preferences({ is_whatsapp_ready: false }), "whatsapp")).toBe(false);
  });
});

describe("telegramChatFor and whatsappNumberFor", () => {
  it("keeps the stored chat while it is linked, else takes the first", () => {
    expect(telegramChatFor(preferences({ telegram_chats: chats, telegram_chat: "1002" }))).toBe("1002");
    expect(telegramChatFor(preferences({ telegram_chats: chats, telegram_chat: "9999" }))).toBe("1001");
    expect(telegramChatFor(preferences())).toBeNull();
  });

  it("starts the number with the stored one, else the sign-in phone", () => {
    expect(whatsappNumberFor(preferences({ whatsapp_number: "+995555000111", suggested_whatsapp_number: "+995555000222" }))).toBe(
      "+995555000111",
    );
    expect(whatsappNumberFor(preferences({ suggested_whatsapp_number: "+995555000222" }))).toBe("+995555000222");
    expect(whatsappNumberFor(preferences())).toBe("");
  });
});

describe("normalizeWhatsAppNumber", () => {
  it("reads typed numbers with their country code", () => {
    expect(normalizeWhatsAppNumber("+995 555 12-34-56")).toBe("+995555123456");
    expect(normalizeWhatsAppNumber("00995 (555) 123456")).toBe("+995555123456");
  });

  it("refuses numbers without a country code or too short", () => {
    expect(normalizeWhatsAppNumber("555 12 34 56")).toBeNull();
    expect(normalizeWhatsAppNumber("+12")).toBeNull();
    expect(normalizeWhatsAppNumber("+0995555123456")).toBeNull();
  });
});
