import { describe, expect, it } from "vitest";

import type { InboxRow } from "./inboxModel";
import {
  isResolvable,
  movedCursor,
  prunedSelection,
  rowsAfterResolving,
  selectionState,
  toggledAll,
  toggledSelection,
  workOf,
} from "./triage";

function row(id: string, patch: Partial<InboxRow> = {}): InboxRow {
  return {
    id,
    contactName: id,
    contactPhone: null,
    channel: "web_chat",
    language: "en",
    status: "open",
    isAfterHours: false,
    isSandbox: false,
    lastMessageText: "Hello",
    lastMessageAttachment: null,
    lastMessageAuthor: "customer",
    lastMessageAt: 1_700_000_000_000_000,
    assigneeUserId: null,
    isAssignedAutomatically: false,
    noteCount: 0,
    handoff: null,
    request: null,
    rating: null,
    ...patch,
  };
}

const handoff = (id: string, status: "notified" | "resolved" = "notified") =>
  ({ id, status, reason: "customer_request", urgency: "normal", created_at: 1 }) as InboxRow["handoff"];
const request = (id: string, status: "new" | "in_progress" | "won" | "lost" = "new") =>
  ({ id, status, lead_type: "banquet", created_at: 1 }) as InboxRow["request"];

const waiting = row("a", { handoff: handoff("h1") });
const asking = row("b", { request: request("l1", "in_progress") });
const both = row("c", { handoff: handoff("h2"), request: request("l2") });
const quiet = row("d");

describe("what Resolved closes on a row", () => {
  it("resolves the open handoff first", () => {
    expect(workOf(waiting)).toEqual({ kind: "handoff", conversationId: "a", handoffId: "h1" });
    expect(workOf(both)).toEqual({ kind: "handoff", conversationId: "c", handoffId: "h2" });
  });

  it("else marks the open request won, remembering its status for Undo", () => {
    expect(workOf(asking)).toEqual({ kind: "request", conversationId: "b", leadId: "l1", status: "in_progress" });
  });

  it("finds nothing in a quiet row, a resolved handoff or a closed request", () => {
    expect(workOf(quiet)).toBeNull();
    expect(workOf(row("e", { handoff: handoff("h3", "resolved") }))).toBeNull();
    expect(workOf(row("f", { request: request("l3", "won") }))).toBeNull();
    expect(isResolvable(quiet)).toBe(false);
    expect(isResolvable(waiting)).toBe(true);
  });
});

describe("the selection", () => {
  const rows = [waiting, asking, both, quiet];

  it("takes only rows with something to resolve, and a second toggle drops them", () => {
    const once = toggledSelection(new Set(), waiting);
    expect([...once]).toEqual(["a"]);
    expect([...toggledSelection(once, quiet)]).toEqual(["a"]);
    expect([...toggledSelection(once, waiting)]).toEqual([]);
  });

  it("selects every resolvable row, and all of them again clears it", () => {
    const all = toggledAll(new Set(), rows);
    expect([...all].sort()).toEqual(["a", "b", "c"]);
    expect(toggledAll(all, rows).size).toBe(0);
    expect(toggledAll(new Set(), [quiet]).size).toBe(0);
  });

  it("says whether none, some or all are chosen", () => {
    expect(selectionState(new Set(), rows)).toBe("none");
    expect(selectionState(new Set(["a"]), rows)).toBe("some");
    expect(selectionState(new Set(["a", "b", "c"]), rows)).toBe("all");
  });

  it("forgets rows gone from the list or with nothing left to resolve, and keeps its identity otherwise", () => {
    const chosen = new Set(["a", "b", "gone"]);
    expect([...prunedSelection(chosen, [waiting, row("b")])]).toEqual(["a"]);
    const kept = new Set(["a", "b"]);
    expect(prunedSelection(kept, rows)).toBe(kept);
  });
});

describe("the keyboard cursor", () => {
  const rows = [waiting, asking, both];

  it("lands on the first row, then moves and stays at the ends", () => {
    expect(movedCursor(rows, null, 1)).toBe("a");
    expect(movedCursor(rows, "a", 1)).toBe("b");
    expect(movedCursor(rows, "c", 1)).toBe("c");
    expect(movedCursor(rows, "a", -1)).toBe("a");
    expect(movedCursor(rows, "c", -1)).toBe("b");
  });

  it("starts again from the first row when its row left the list, and has nowhere to go in an empty one", () => {
    expect(movedCursor(rows, "gone", 1)).toBe("a");
    expect(movedCursor([], null, 1)).toBeNull();
  });
});

describe("rows leaving the view once resolved", () => {
  const rows = [waiting, asking, both, quiet];
  const done = new Set(["a", "b", "c", "d"]);

  it("a resolved handoff leaves Needs a person", () => {
    expect(rowsAfterResolving("needs_person", rows, done)).toEqual(["a", "c"]);
  });

  it("a won request leaves Requests, unless a handoff was resolved instead", () => {
    expect(rowsAfterResolving("requests", rows, done)).toEqual(["b"]);
  });

  it("other views keep their rows, and nothing leaves that was not resolved", () => {
    expect(rowsAfterResolving("mine", rows, done)).toEqual([]);
    expect(rowsAfterResolving("all", rows, done)).toEqual([]);
    expect(rowsAfterResolving("needs_person", rows, new Set(["b"]))).toEqual([]);
  });
});
