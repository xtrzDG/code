import { describe, expect, it } from "vitest";

import {
  EMPTY_CONNECT_FORM,
  accountLabel,
  buildConnectBody,
  channelPathName,
  channelState,
  dialHref,
  findChannel,
  formatLinkCode,
  isChannelInPlan,
  isChannelOn,
  notificationLanguages,
  sortForwardingCodes,
  startCommand,
  upsertChannel,
  type ChannelView,
} from "./channels";

const channel = (overrides: Partial<ChannelView>): ChannelView => ({
  id: "channel_1",
  business_id: "business_1",
  channel: "telegram",
  status: "connected",
  has_credential: true,
  updated_at: 1_790_000_000_000_000,
  ...overrides,
});

describe("channel state", () => {
  it("names the website chat 'web' in the path", () => {
    expect(channelPathName("web_chat")).toBe("web");
    expect(channelPathName("telegram")).toBe("telegram");
  });

  it("reports a channel that was never connected", () => {
    expect(channelState(undefined)).toBe("not_connected");
    expect(channelState(channel({ status: "error" }))).toBe("error");
  });

  it("treats every status but disabled as on", () => {
    expect(isChannelOn(undefined)).toBe(false);
    expect(isChannelOn(channel({ status: "disabled" }))).toBe(false);
    expect(isChannelOn(channel({ status: "pending" }))).toBe(true);
    expect(isChannelOn(channel({ status: "error" }))).toBe(true);
  });

  it("finds and replaces channels by kind", () => {
    const list = [channel({ channel: "telegram" }), channel({ id: "channel_2", channel: "phone" })];
    expect(findChannel(list, "phone")?.id).toBe("channel_2");
    expect(findChannel(list, "whatsapp")).toBeUndefined();

    const updated = upsertChannel(list, channel({ channel: "phone", status: "disabled" }));
    expect(updated).toHaveLength(2);
    expect(findChannel(updated, "phone")?.status).toBe("disabled");
    expect(upsertChannel(undefined, channel({ channel: "web_chat" }))).toHaveLength(1);
  });

  it("shows bot usernames with @", () => {
    expect(accountLabel("telegram", "cafe_bot")).toBe("@cafe_bot");
    expect(accountLabel("telegram", "@cafe_bot")).toBe("@cafe_bot");
    expect(accountLabel("phone", "+995322000000")).toBe("+995322000000");
    expect(accountLabel("phone", null)).toBeNull();
  });
});

describe("buildConnectBody", () => {
  it("sends nothing for the website chat", () => {
    expect(buildConnectBody("web_chat", EMPTY_CONNECT_FORM)).toEqual({ ok: true, body: {} });
  });

  it("checks the BotFather token shape", () => {
    expect(buildConnectBody("telegram", EMPTY_CONNECT_FORM)).toEqual({ ok: false, errors: { botToken: "required" } });
    expect(buildConnectBody("telegram", { ...EMPTY_CONNECT_FORM, botToken: "12345:short" })).toEqual({
      ok: false,
      errors: { botToken: "botToken" },
    });
    const token = "123456789:AAH7d0bS1F0bQZ8yX5n4k3j2h1g0f9e8d7c";
    expect(buildConnectBody("telegram", { ...EMPTY_CONNECT_FORM, botToken: ` ${token} ` })).toEqual({
      ok: true,
      body: { bot_token: token },
    });
  });

  it("needs a numeric WhatsApp phone number id; the account id is optional", () => {
    expect(buildConnectBody("whatsapp", { ...EMPTY_CONNECT_FORM, phoneNumberId: "12a" })).toEqual({
      ok: false,
      errors: { phoneNumberId: "digits" },
    });
    expect(buildConnectBody("whatsapp", { ...EMPTY_CONNECT_FORM, phoneNumberId: "1055" })).toEqual({
      ok: true,
      body: { phone_number_id: "1055" },
    });
    expect(
      buildConnectBody("whatsapp", { ...EMPTY_CONNECT_FORM, phoneNumberId: "1055", businessAccountId: "77" }),
    ).toEqual({ ok: true, body: { phone_number_id: "1055", whatsapp_business_account_id: "77" } });
  });

  it("needs a page id and a page token for Messenger and Instagram", () => {
    expect(buildConnectBody("instagram", EMPTY_CONNECT_FORM)).toEqual({
      ok: false,
      errors: { pageId: "required", pageAccessToken: "required" },
    });
    expect(buildConnectBody("messenger", { ...EMPTY_CONNECT_FORM, pageId: "42", pageAccessToken: "short token" })).toEqual({
      ok: false,
      errors: { pageAccessToken: "pageToken" },
    });
    const token = "EAAB" + "x".repeat(40);
    expect(buildConnectBody("messenger", { ...EMPTY_CONNECT_FORM, pageId: "42", pageAccessToken: token })).toEqual({
      ok: true,
      body: { page_id: "42", page_access_token: token },
    });
  });

  it("sends the phone number as typed with the country as a hint", () => {
    expect(buildConnectBody("phone", EMPTY_CONNECT_FORM)).toEqual({ ok: false, errors: { phoneNumber: "required" } });
    expect(buildConnectBody("phone", { ...EMPTY_CONNECT_FORM, phoneNumber: "032 200 00 00", countryHint: "ge" })).toEqual({
      ok: true,
      body: { phone_number: "032 200 00 00", country_hint: "GE" },
    });
    expect(buildConnectBody("phone", { ...EMPTY_CONNECT_FORM, phoneNumber: "+1 415 555 0100" })).toEqual({
      ok: true,
      body: { phone_number: "+1 415 555 0100" },
    });
  });
});

describe("call forwarding", () => {
  it("orders the codes and escapes # for the dialer", () => {
    const sorted = sortForwardingCodes([
      { condition: "cancel_all" as const },
      { condition: "busy" as const },
      { condition: "no_answer" as const },
      { condition: "unreachable" as const },
    ]);
    expect(sorted.map((code) => code.condition)).toEqual(["no_answer", "busy", "unreachable", "cancel_all"]);
    expect(dialHref("**61*+995322000000#")).toBe("tel:**61*+995322000000%23");
    expect(dialHref("##002#")).toBe("tel:%23%23002%23");
  });
});

describe("staff Telegram link", () => {
  it("groups the code for reading", () => {
    expect(formatLinkCode("ABCDE12345")).toBe("ABCDE 12345");
    expect(formatLinkCode("ABC")).toBe("ABC");
    expect(startCommand("ABCDE12345")).toBe("/start ABCDE12345");
  });

  it("offers the owner's language first, without repeats", () => {
    expect(notificationLanguages("ka", ["ka", "en", "ru"])).toEqual(["ka", "en", "ru"]);
    expect(notificationLanguages("ru", ["de"])).toEqual(["ru", "de"]);
  });
});

describe("plans", () => {
  it("knows which channels a plan covers", () => {
    expect(isChannelInPlan(["telegram", "web_chat"], "phone")).toBe(false);
    expect(isChannelInPlan(["phone"], "phone")).toBe(true);
    expect(isChannelInPlan(undefined, "phone")).toBe(true);
  });
});
