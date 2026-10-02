import { describe, expect, it } from "vitest";

import {
  accountLabel,
  channelPathName,
  channelState,
  dialHref,
  findChannel,
  formatLinkCode,
  isChannelInPlan,
  isChannelOn,
  markChannelDisabled,
  notificationLanguages,
  sortForwardingCodes,
  startCommand,
  upsertChannel,
  type ChannelView,
} from "./channels";
import { buildConnectBody, EMPTY_CONNECT_FORM } from "./connectForm";
import {
  buildWidgetPreviewUrl,
  isSameWidgetLook,
  normalizeHexColor,
  readableTextColor,
  savedWidgetLook,
  WIDGET_COLOR_PRESETS,
  WIDGET_DEFAULT_COLOR,
} from "./widgetLook";
import { buildStaffTemplateBody } from "./staffTemplate";
import { readCalendarReturn, withoutCalendarReturn } from "./calendarReturn";

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

  it("marks a disconnected channel off without its credential", () => {
    const list = [channel({ channel: "telegram", account_id: "cafe_bot" }), channel({ id: "channel_2", channel: "phone" })];
    const updated = markChannelDisabled(list, "telegram");
    expect(findChannel(updated, "telegram")).toMatchObject({ status: "disabled", has_credential: false, account_id: null });
    expect(findChannel(updated, "phone")?.status).toBe("connected");
    expect(markChannelDisabled(undefined, "telegram")).toEqual([]);
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

describe("website chat look", () => {
  it("normalizes hex colours to the API's six-digit form", () => {
    expect(normalizeHexColor("#0F766E")).toBe("#0f766e");
    expect(normalizeHexColor(" 0f766e ")).toBe("#0f766e");
    expect(normalizeHexColor("#abc")).toBe("#aabbcc");
    expect(normalizeHexColor("red")).toBeNull();
    expect(normalizeHexColor("#12345")).toBeNull();
    expect(normalizeHexColor("")).toBeNull();
  });

  it("picks readable text on the accent like the widget does", () => {
    expect(readableTextColor("#4f46e5")).toBe("#ffffff");
    expect(readableTextColor("#fde047")).toBe("#111827");
    expect(readableTextColor("not a colour")).toBe("#ffffff");
    // Mid-tone brand colours: dark text has the higher contrast.
    for (const accent of ["#f97316", "#f59e0b", "#22c55e", "#06b6d4"]) {
      expect(readableTextColor(accent)).toBe("#111827");
    }
    for (const preset of WIDGET_COLOR_PRESETS) {
      expect(readableTextColor(preset)).toBe("#ffffff");
    }
  });

  it("fills the widget defaults into the saved look", () => {
    expect(savedWidgetLook(undefined)).toEqual({ color: WIDGET_DEFAULT_COLOR, position: "right" });
    expect(savedWidgetLook(channel({ channel: "web_chat", widget_color: "#0F766E", widget_position: "left" }))).toEqual({
      color: "#0f766e",
      position: "left",
    });
    expect(isSameWidgetLook({ color: "#0F766E", position: "left" }, { color: "#0f766e", position: "left" })).toBe(true);
    expect(isSameWidgetLook({ color: "#0f766e", position: "left" }, { color: "#0f766e", position: "right" })).toBe(false);
  });

  it("builds the live preview link with unsaved choices", () => {
    const url = buildWidgetPreviewUrl(
      "https://api.example.com/widget/demo?business_id=business_1",
      { color: "#0F766E", position: "left" },
      "ka",
    );
    const parsed = new URL(url);

    expect(parsed.origin + parsed.pathname).toBe("https://api.example.com/widget/demo");
    expect(parsed.searchParams.get("business_id")).toBe("business_1");
    expect(parsed.searchParams.get("color")).toBe("#0f766e");
    expect(parsed.searchParams.get("position")).toBe("left");
    expect(parsed.searchParams.get("language")).toBe("ka");
  });
});

describe("Google Calendar return", () => {
  it("reads the outcome the API's callback put in the address", () => {
    expect(readCalendarReturn("?calendar=connected")).toEqual({ kind: "connected" });
    expect(readCalendarReturn("?calendar=error&reason=access_denied")).toEqual({ kind: "error", reason: "access_denied" });
    expect(readCalendarReturn("?calendar=error&reason=whatever")).toEqual({ kind: "error", reason: "unknown" });
    expect(readCalendarReturn("?calendar=error")).toEqual({ kind: "error", reason: "unknown" });
    expect(readCalendarReturn("")).toBeNull();
    expect(readCalendarReturn("?tab=x")).toBeNull();
  });

  it("removes only the notice from the query", () => {
    expect(withoutCalendarReturn("?calendar=error&reason=link_expired&tab=x")).toBe("tab=x");
    expect(withoutCalendarReturn("?calendar=connected")).toBe("");
  });
});

describe("WhatsApp template for staff replies", () => {
  it("is saved with its name and approved language", () => {
    expect(buildStaffTemplateBody(" staff_reply ", "en")).toEqual({
      ok: true,
      body: { name: "staff_reply", language_code: "en" },
    });
    expect(buildStaffTemplateBody("staff_reply", "pt-br")).toEqual({
      ok: true,
      body: { name: "staff_reply", language_code: "pt_BR" },
    });
  });

  it("names what is missing or malformed", () => {
    expect(buildStaffTemplateBody("", "")).toEqual({ ok: false, errors: { name: "required", language: "required" } });
    expect(buildStaffTemplateBody("Staff Reply", "english")).toEqual({
      ok: false,
      errors: { name: "name", language: "language" },
    });
  });
});
