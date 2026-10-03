import { describe, expect, it } from "vitest";

import type { ConversationSummaryView } from "@/components/insights/types";

import {
  clearedFilters,
  DEFAULT_INBOX_FILTERS,
  historyFilterCount,
  inboxApiQuery,
  inboxFiltersQuery,
  parseInboxFilters,
  rowFromConversation,
  rowFromInboxItem,
  sheetFilterCount,
  usesConversationFeed,
  viewCount,
  viewOnly,
  withSearch,
  withView,
  type InboxFilters,
} from "./inboxModel";
import type { InboxItemView } from "./types";

const filtersOf = (query: string) => parseInboxFilters(new URLSearchParams(query));

describe("the inbox filters in the URL", () => {
  it("open on Needs a person without a query", () => {
    expect(filtersOf("")).toEqual(DEFAULT_INBOX_FILTERS);
    expect(DEFAULT_INBOX_FILTERS.view).toBe("needs_person");
    expect(inboxFiltersQuery(DEFAULT_INBOX_FILTERS)).toBe("");
  });

  it("read a view and an unknown one falls back to the default", () => {
    expect(filtersOf("view=mine").view).toBe("mine");
    expect(filtersOf("view=archive").view).toBe("needs_person");
  });

  it("keep the history filters only on All", () => {
    const onAll = filtersOf("view=all&status=open&period=7d&q=Nino&test=1&channel=whatsapp");
    expect(onAll).toMatchObject({ view: "all", status: "open", period: "7d", search: "Nino", includeTest: true, channel: "whatsapp" });
    expect(inboxFiltersQuery(onAll)).toBe("view=all&channel=whatsapp&status=open&period=7d&q=Nino&test=1");

    const onMine = filtersOf("view=mine&status=open&q=Nino&channel=whatsapp");
    expect(onMine).toMatchObject({ view: "mine", status: null, search: "", channel: "whatsapp" });
    expect(inboxFiltersQuery(onMine)).toBe("view=mine&channel=whatsapp");
  });
});

describe("moving between views", () => {
  const onAll: InboxFilters = { ...DEFAULT_INBOX_FILTERS, view: "all", status: "open", search: "Nino", channel: "telegram" };

  it("keeps the channel and drops the history filters off All", () => {
    expect(withView(onAll, "requests")).toEqual({ ...DEFAULT_INBOX_FILTERS, view: "requests", channel: "telegram" });
    expect(withView(onAll, "all")).toEqual(onAll);
  });

  it("sends a search to All, and an empty one leaves the view as it is", () => {
    expect(withSearch(DEFAULT_INBOX_FILTERS, "Anna").view).toBe("all");
    expect(withSearch({ ...DEFAULT_INBOX_FILTERS, view: "mine" }, "  ").view).toBe("mine");
  });

  it("clears the sheet's filters but keeps the search on All", () => {
    expect(clearedFilters(onAll)).toEqual({ ...DEFAULT_INBOX_FILTERS, view: "all", search: "Nino" });
    expect(viewOnly(onAll)).toEqual({ ...DEFAULT_INBOX_FILTERS, view: "all" });
  });
});

describe("which API answers", () => {
  it("is the inbox for a view and the conversation feed for a search or history filter", () => {
    expect(usesConversationFeed(DEFAULT_INBOX_FILTERS)).toBe(false);
    expect(usesConversationFeed({ ...DEFAULT_INBOX_FILTERS, view: "all" })).toBe(false);
    expect(usesConversationFeed({ ...DEFAULT_INBOX_FILTERS, view: "all", search: "Nino" })).toBe(true);
    expect(usesConversationFeed({ ...DEFAULT_INBOX_FILTERS, view: "all", period: "30d" })).toBe(true);
    // Off All the history filters do not hold, so the inbox answers.
    expect(usesConversationFeed({ ...DEFAULT_INBOX_FILTERS, view: "mine", search: "Nino" })).toBe(false);
  });

  it("asks the inbox for the view and the channel only", () => {
    expect(inboxApiQuery(DEFAULT_INBOX_FILTERS)).toEqual({ view: "needs_person" });
    expect(inboxApiQuery({ ...DEFAULT_INBOX_FILTERS, view: "unassigned", channel: "phone" })).toEqual({
      view: "unassigned",
      channel: "phone",
    });
  });

  it("counts the filters on the Filters button without the search", () => {
    const filters: InboxFilters = { ...DEFAULT_INBOX_FILTERS, view: "all", channel: "web_chat", status: "open", search: "x" };
    expect(historyFilterCount(filters)).toBe(2);
    expect(sheetFilterCount(filters)).toBe(2);
    expect(sheetFilterCount({ ...filters, view: "mine" })).toBe(1);
    expect(historyFilterCount({ ...filters, view: "mine" })).toBe(0);
  });
});

describe("the view counts", () => {
  const counts = { needs_person: 3, requests: 1, mine: 0, unassigned: 2 };

  it("show each work view's number and none on All", () => {
    expect(viewCount("needs_person", counts)).toBe(3);
    expect(viewCount("mine", counts)).toBe(0);
    expect(viewCount("all", counts)).toBeUndefined();
    expect(viewCount("requests", null)).toBeUndefined();
  });
});

describe("one row shape for both answers", () => {
  it("takes the team fields from an inbox item", () => {
    const item = {
      id: "conversation_1",
      business_id: "business_1",
      contact_id: "contact_1",
      contact_name: "Nino",
      channel: "whatsapp",
      status: "handoff",
      is_after_hours: true,
      last_message_at: 10,
      last_message_text: "Hello",
      last_message_author: "customer",
      assignee_user_id: "user_2",
      assignment_revision: 3,
      is_assigned_automatically: true,
      awaits_team: true,
      has_open_request: false,
      note_count: 2,
      created_at: 1,
    } as unknown as InboxItemView;
    expect(rowFromInboxItem(item)).toMatchObject({
      id: "conversation_1",
      contactName: "Nino",
      contactPhone: null,
      isSandbox: false,
      assigneeUserId: "user_2",
      isAssignedAutomatically: true,
      noteCount: 2,
      handoff: null,
      request: null,
      rating: null,
    });
  });

  it("leaves the assignment unknown for a conversation of the feed", () => {
    const conversation = {
      id: "conversation_2",
      channel: "web_chat",
      status: "open",
      is_after_hours: false,
      is_sandbox: true,
      last_message_at: 5,
      rating: "good",
    } as unknown as ConversationSummaryView;
    const row = rowFromConversation(conversation);
    expect(row.assigneeUserId).toBeUndefined();
    expect(row).toMatchObject({ isSandbox: true, noteCount: 0, rating: "good", lastMessageText: null });
  });
});
