import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { lookupMessage } from "@/i18n/translate";
import type { MessageView, StaffReplyView } from "@/components/insights/types";

import {
  CALL_OUTCOMES,
  callRecordingUrl,
  canReplyFromCard,
  conversationApiQuery,
  conversationFiltersQuery,
  DEFAULT_CONVERSATION_FILTERS,
  formatCallDuration,
  groupMessagesByDay,
  initialsOf,
  isSendableReply,
  isSendableTemplateReply,
  isWindowClosingSoon,
  MAX_REPLY_LENGTH,
  messageSide,
  offeredTemplate,
  parseConversationFilters,
  prettyJson,
  REPLY_BLOCKS,
  templateLanguageName,
  templateReplyLength,
  templateReplyText,
} from "./conversationModel";
import { usageTotals } from "./conversationUsage";

const NOON_OCT_1_TBILISI = Date.UTC(2026, 9, 1, 8) * 1000;

function message(overrides: Partial<MessageView>): MessageView {
  return {
    id: "message_1",
    direction: "inbound",
    author: "customer",
    text: "",
    language: null,
    tool_calls: [],
    model_id: null,
    input_tokens: 0,
    output_tokens: 0,
    cost_micro_usd: 0,
    created_at: NOON_OCT_1_TBILISI,
    ...overrides,
  };
}

describe("conversation filters in the URL", () => {
  it("round-trip without the defaults", () => {
    const filters = { ...DEFAULT_CONVERSATION_FILTERS, channel: "telegram" as const, period: "7d" as const, search: " Nino " };
    const query = conversationFiltersQuery(filters);
    expect(query).toBe("channel=telegram&period=7d&q=Nino");
    expect(parseConversationFilters(new URLSearchParams(query))).toEqual({ ...filters, search: "Nino" });
    expect(conversationFiltersQuery(DEFAULT_CONVERSATION_FILTERS)).toBe("");
  });

  it("ignore unknown values", () => {
    expect(parseConversationFilters(new URLSearchParams("channel=fax&status=x&period=1y&test=yes"))).toEqual(
      DEFAULT_CONVERSATION_FILTERS,
    );
  });
});

describe("feed query", () => {
  it("sends every filter to the API, the period as local dates", () => {
    expect(conversationApiQuery(DEFAULT_CONVERSATION_FILTERS, "2026-10-01")).toEqual({});
    expect(
      conversationApiQuery(
        { channel: "telegram", status: "handoff", period: "7d", search: "  599 11 ", includeTest: true },
        "2026-10-01",
      ),
    ).toEqual({ channel: "telegram", status: "handoff", from: "2026-09-25", search: "599 11", include_sandbox: "true" });
    expect(conversationApiQuery({ ...DEFAULT_CONVERSATION_FILTERS, period: "today" }, "2026-10-01")).toEqual({
      from: "2026-10-01",
    });
  });
});

describe("calls and replies", () => {
  it("formats call durations", () => {
    expect(formatCallDuration(95)).toBe("1:35");
    expect(formatCallDuration(5)).toBe("0:05");
    expect(formatCallDuration(3723)).toBe("1:02:03");
  });

  it("has a text for every call outcome and reply block", () => {
    const keys = [...Object.values(CALL_OUTCOMES), ...Object.values(REPLY_BLOCKS)];
    expect(keys.filter((key) => typeof lookupMessage(en, key) !== "string")).toEqual([]);
  });

  it("accepts visible text within the limit", () => {
    expect(isSendableReply("Hi")).toBe(true);
    expect(isSendableReply("  \n ")).toBe(false);
    expect(isSendableReply("x".repeat(MAX_REPLY_LENGTH + 1))).toBe(false);
  });

  it("warns in the last hour of the 24-hour window", () => {
    const now = Date.UTC(2026, 9, 1, 12);
    expect(isWindowClosingSoon((now + 30 * 60_000) * 1000, now)).toBe(true);
    expect(isWindowClosingSoon((now + 3 * 3_600_000) * 1000, now)).toBe(false);
    expect(isWindowClosingSoon((now - 1000) * 1000, now)).toBe(false);
    expect(isWindowClosingSoon(null, now)).toBe(false);
  });
});

describe("transcript", () => {
  it("groups messages by the business day in time order", () => {
    const late = Date.UTC(2026, 9, 1, 21) * 1000; // already Oct 2 in Tbilisi
    const days = groupMessagesByDay(
      [message({ id: "b", created_at: late }), message({ id: "a" }), message({ id: "c", created_at: late + 1 })],
      "Asia/Tbilisi",
    );
    expect(days.map((day) => [day.date, day.messages.map((item) => item.id)])).toEqual([
      ["2026-10-01", ["a"]],
      ["2026-10-02", ["b", "c"]],
    ]);
  });

  it("puts the customer and the business on opposite sides", () => {
    expect(messageSide("customer")).toBe("start");
    expect(messageSide("assistant")).toBe("end");
    expect(messageSide("staff")).toBe("end");
    expect(messageSide("system")).toBe("center");
  });

  it("indents tool JSON and keeps other text", () => {
    expect(prettyJson('{"a":1}')).toBe('{\n  "a": 1\n}');
    expect(prettyJson("not json")).toBe("not json");
  });

  it("sums model usage", () => {
    expect(
      usageTotals([
        message({ input_tokens: 100, output_tokens: 20, cost_micro_usd: 300 }),
        message({ input_tokens: 50, output_tokens: 5, cost_micro_usd: 100 }),
      ]),
    ).toEqual({ inputTokens: 150, outputTokens: 25, costMicroUsd: 400 });
  });

  it("makes avatar initials from names in any script", () => {
    expect(initialsOf("Nino Beridze")).toBe("NB");
    expect(initialsOf("ნინო")).toBe("ნ");
    expect(initialsOf("алексей петров иванович")).toBe("АП");
    expect(initialsOf(null)).toBe("#");
    expect(initialsOf("+995 599")).toBe("#");
    expect(initialsOf("أحمد الخطيب")).toBe("أ");
    expect(initialsOf("נועה כהן")).toBe("נכ");
  });
});

describe("call recordings", () => {
  it("are played through the cabinet's API proxy", () => {
    expect(callRecordingUrl("business_1", "call_9")).toBe("/api/backend/v1/businesses/business_1/calls/call_9/recording");
    expect(callRecordingUrl("b/1", "c?2")).toBe("/api/backend/v1/businesses/b%2F1/calls/c%3F2/recording");
  });
});

describe("replies sent as a WhatsApp template", () => {
  it("travel as one line, as the API sends them", () => {
    expect(templateReplyText("  Ready.\n\n\tSee you\r\n at  8 ")).toBe("Ready. See you at 8");
    expect(templateReplyLength("a\nb")).toBe(3);
    // Characters, not UTF-16 units: an emoji counts once, like the API counts it.
    expect(templateReplyLength("🍕🍕")).toBe(2);
  });

  it("fit the template's single parameter", () => {
    expect(isSendableTemplateReply("Hello", 1024)).toBe(true);
    expect(isSendableTemplateReply(" \n ", 1024)).toBe(false);
    expect(isSendableTemplateReply("x".repeat(1025), 1024)).toBe(false);
    expect(isSendableTemplateReply("x\n".repeat(512), 1024)).toBe(true);
  });
});

describe("template languages", () => {
  it("are named in the interface language with their code", () => {
    expect(templateLanguageName("en_US", "en")).toBe("American English (en_US)");
    expect(templateLanguageName("ka", "en")).toBe("Georgian (ka)");
    expect(templateLanguageName("ru", "ru")).toBe("русский (ru)");
    expect(templateLanguageName("zz_ZZ", "en")).toContain("zz_ZZ");
  });
});

describe("whether the reply box takes text", () => {
  const template = { name: "staff_reply", language_code: "pt_BR", max_text_length: 1024 };

  it("takes it in an open channel and in the owner's template after the window", () => {
    const open: StaffReplyView = { is_available: true, delivery: "sent" };
    const closedWithTemplate: StaffReplyView = { is_available: false, block: "window_closed", template };

    expect(canReplyFromCard(open)).toBe(true);
    expect(offeredTemplate(open)).toBeNull();
    // A booking confirmation goes into the box, not into the copy-it-yourself dialog.
    expect(canReplyFromCard(closedWithTemplate)).toBe(true);
    expect(offeredTemplate(closedWithTemplate)).toEqual(template);
  });

  it("does not take it without a template, in calls, or without a reply view", () => {
    expect(canReplyFromCard({ is_available: false, block: "window_closed" })).toBe(false);
    expect(canReplyFromCard({ is_available: false, block: "voice_call" })).toBe(false);
    expect(canReplyFromCard({ is_available: false, block: "channel_disconnected", template })).toBe(false);
    expect(canReplyFromCard(null)).toBe(false);
  });
});
