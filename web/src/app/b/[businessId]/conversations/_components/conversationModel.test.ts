import { describe, expect, it } from "vitest";

import type { ConversationSummaryView, MessageView } from "@/components/insights/types";

import {
  conversationFiltersQuery,
  DEFAULT_CONVERSATION_FILTERS,
  filterConversations,
  groupMessagesByDay,
  initialsOf,
  matchesSearch,
  messageSide,
  parseConversationFilters,
  prettyJson,
  usageTotals,
} from "./conversationModel";

const US_PER_HOUR = 3_600_000_000;
const NOON_OCT_1_TBILISI = Date.UTC(2026, 9, 1, 8) * 1000;

function conversation(overrides: Partial<ConversationSummaryView>): ConversationSummaryView {
  return {
    id: "conversation_1",
    business_id: "business_1",
    contact_id: "contact_1",
    contact_name: null,
    contact_phone_number: null,
    assistant_version_id: "assistant_version_1",
    channel: "whatsapp",
    language: "ka",
    status: "open",
    is_after_hours: false,
    is_sandbox: false,
    message_count: 2,
    last_message_text: null,
    last_message_at: NOON_OCT_1_TBILISI,
    created_at: NOON_OCT_1_TBILISI,
    ...overrides,
  };
}

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

describe("search", () => {
  const item = conversation({ contact_name: "Ninó Beridze", contact_phone_number: "+995599112233", last_message_text: "Столик на субботу" });

  it("matches names without accents and case, and message text in any script", () => {
    expect(matchesSearch(item, "nino")).toBe(true);
    expect(matchesSearch(item, "СУББОТУ")).toBe(true);
    expect(matchesSearch(item, "giorgi")).toBe(false);
    expect(matchesSearch(item, "  ")).toBe(true);
  });

  it("matches phone digits whatever the formatting", () => {
    expect(matchesSearch(item, "599 11 22")).toBe(true);
    expect(matchesSearch(item, "(599) 112-233")).toBe(true);
    expect(matchesSearch(item, "12")).toBe(false);
  });
});

describe("client-side filtering", () => {
  const context = { today: "2026-10-01", timeZone: "Asia/Tbilisi" };
  const items = [
    conversation({ id: "today", status: "open" }),
    conversation({ id: "handoff-3-days", status: "handoff", last_message_at: NOON_OCT_1_TBILISI - 72 * US_PER_HOUR }),
    conversation({ id: "old", status: "closed", last_message_at: NOON_OCT_1_TBILISI - 40 * 24 * US_PER_HOUR }),
  ];

  it("filters by status and by the local date of the last message", () => {
    const ids = (filters: Partial<typeof DEFAULT_CONVERSATION_FILTERS>) =>
      filterConversations(items, { ...DEFAULT_CONVERSATION_FILTERS, ...filters }, context).map((item) => item.id);
    expect(ids({})).toEqual(["today", "handoff-3-days", "old"]);
    expect(ids({ period: "today" })).toEqual(["today"]);
    expect(ids({ period: "7d" })).toEqual(["today", "handoff-3-days"]);
    expect(ids({ status: "handoff" })).toEqual(["handoff-3-days"]);
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
  });
});
