/**
 * Pure rules of triage in the inbox list: what "Resolved" does to a row
 * (its open handoff is resolved, else its open request is marked won),
 * how the selection follows the list, where the keyboard cursor goes, and
 * which rows leave the view once resolved.
 */

import type { LeadStatus } from "@/components/insights/types";
import type { InboxView } from "@/lib/navigation";

import type { InboxRow } from "./inboxModel";

/** What resolving a row changes, through the existing endpoints (each with its own Undo). */
export type RowWork =
  | { kind: "handoff"; conversationId: string; handoffId: string }
  | { kind: "request"; conversationId: string; leadId: string; status: LeadStatus };

const OPEN_REQUEST: readonly LeadStatus[] = ["new", "in_progress"];

/** The work a "Resolved" on this row closes, or null when nothing waits in it. */
export function workOf(row: InboxRow): RowWork | null {
  if (row.handoff && row.handoff.status !== "resolved") {
    return { kind: "handoff", conversationId: row.id, handoffId: row.handoff.id };
  }
  if (row.request && OPEN_REQUEST.includes(row.request.status)) {
    return { kind: "request", conversationId: row.id, leadId: row.request.id, status: row.request.status };
  }
  return null;
}

export function isResolvable(row: InboxRow): boolean {
  return workOf(row) !== null;
}

/** The selection kept to rows still shown and still resolvable (a reload or another view). */
export function prunedSelection(selection: ReadonlySet<string>, rows: readonly InboxRow[]): ReadonlySet<string> {
  const kept = new Set(rows.filter((row) => selection.has(row.id) && isResolvable(row)).map((row) => row.id));
  return kept.size === selection.size ? selection : kept;
}

/** The selection with one row in or out (only resolvable rows can be chosen). */
export function toggledSelection(selection: ReadonlySet<string>, row: InboxRow): ReadonlySet<string> {
  const next = new Set(selection);
  if (next.has(row.id)) {
    next.delete(row.id);
  } else if (isResolvable(row)) {
    next.add(row.id);
  }
  return next;
}

/** Every resolvable row of the list, or none when they are all chosen already. */
export function toggledAll(selection: ReadonlySet<string>, rows: readonly InboxRow[]): ReadonlySet<string> {
  const resolvable = rows.filter(isResolvable).map((row) => row.id);
  const isAll = resolvable.length > 0 && resolvable.every((id) => selection.has(id));
  return isAll ? new Set() : new Set(resolvable);
}

/** "all", "some" or "none" of the resolvable rows chosen (the select-all box). */
export function selectionState(selection: ReadonlySet<string>, rows: readonly InboxRow[]): "all" | "some" | "none" {
  const resolvable = rows.filter(isResolvable);
  const chosen = resolvable.filter((row) => selection.has(row.id)).length;
  if (chosen === 0) {
    return "none";
  }
  return chosen === resolvable.length ? "all" : "some";
}

/**
 * The row the keyboard cursor moves to: `step` rows on from the cursor
 * (or from the open conversation), staying on the first and last row.
 * The first press without a cursor lands on the first row.
 */
export function movedCursor(rows: readonly InboxRow[], cursorId: string | null, step: number): string | null {
  if (rows.length === 0) {
    return null;
  }
  const index = cursorId === null ? -1 : rows.findIndex((row) => row.id === cursorId);
  if (index === -1) {
    return rows[0]!.id;
  }
  return rows[Math.min(rows.length - 1, Math.max(0, index + step))]!.id;
}

/**
 * Rows that leave the view once their work is resolved: a resolved handoff
 * leaves Needs a person, a closed request leaves Requests. Other views keep
 * the conversation (it is still theirs) and reload with the change.
 */
export function rowsAfterResolving(view: InboxView, rows: readonly InboxRow[], resolvedIds: ReadonlySet<string>): string[] {
  if (view !== "needs_person" && view !== "requests") {
    return [];
  }
  return rows
    .filter((row) => resolvedIds.has(row.id))
    .filter((row) => {
      const work = workOf(row);
      return view === "needs_person" ? work?.kind === "handoff" : work?.kind === "request" && !row.handoff;
    })
    .map((row) => row.id);
}
