"use client";

/**
 * Triage from the inbox list, through the endpoints the conversation card
 * uses: "Resolved" on one row (e) or on every selected row resolves each
 * open handoff (POST …/handoffs/{id}/resolve) and marks each open request
 * won (PATCH …/leads/{id}); the toast's Undo reopens the handoffs (POST
 * …/reopen) and gives the requests their status back. "Take it" (a)
 * assigns the row to me with the revision the list saw.
 *
 * Rows that leave the view (a resolved handoff on Needs a person) go from
 * the list at once; the lists, counts and dashboard then load again.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { InboxView } from "@/lib/navigation";

import type { InboxRow } from "./inboxModel";
import { rowsAfterResolving, workOf, type RowWork } from "./triage";
import type { InboxList } from "./useInboxList";

const NO_IDS: ReadonlySet<string> = new Set();

export function useTriageActions(view: InboxView, list: InboxList) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business, me } = useBusiness();
  const businessId = business.id;
  const [busyIds, setBusyIds] = useState<ReadonlySet<string>>(NO_IDS);

  const refresh = (conversationIds: Iterable<string>) => {
    queryCache.invalidate(queryKeys.conversations.inboxAll(businessId));
    queryCache.invalidate(queryKeys.inbox.all(businessId));
    queryCache.invalidate(queryKeys.dashboard.all(businessId));
    queryCache.invalidate(queryKeys.handoffs.all(businessId), { refetchActive: false });
    queryCache.invalidate(queryKeys.leads.all(businessId), { refetchActive: false });
    for (const id of conversationIds) {
      queryCache.invalidate(queryKeys.conversations.detail(businessId, id));
    }
  };

  const close = (work: RowWork) =>
    work.kind === "handoff"
      ? unwrap(
          api.POST("/v1/businesses/{business_id}/handoffs/{handoff_id}/resolve", {
            params: { path: { business_id: businessId, handoff_id: work.handoffId } },
          }),
        )
      : unwrap(
          api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}", {
            params: { path: { business_id: businessId, lead_id: work.leadId } },
            body: { status: "won" },
          }),
        );

  const reopen = (work: RowWork) =>
    work.kind === "handoff"
      ? unwrap(
          api.POST("/v1/businesses/{business_id}/handoffs/{handoff_id}/reopen", {
            params: { path: { business_id: businessId, handoff_id: work.handoffId } },
          }),
        )
      : unwrap(
          api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}", {
            params: { path: { business_id: businessId, lead_id: work.leadId } },
            body: { status: work.status },
          }),
        );

  const undo = async (done: readonly RowWork[]) => {
    const results = await Promise.allSettled(done.map(reopen));
    refresh(done.map((work) => work.conversationId));
    if (results.every((result) => result.status === "fulfilled")) {
      toast.success(t("inboxTriage.undone"));
    } else {
      toast.success(t("inboxTriage.undonePartly"));
    }
  };

  /** Resolves the work of `rows`; true when every one was resolved. */
  const resolve = async (rows: readonly InboxRow[]): Promise<boolean> => {
    const works = rows.map(workOf).filter((work): work is RowWork => work !== null);
    if (works.length === 0) {
      toast.success(t("inboxTriage.nothingToResolve"));
      return false;
    }
    const ids = new Set(works.map((work) => work.conversationId));
    setBusyIds(ids);
    const results = await Promise.allSettled(works.map(close));
    setBusyIds(NO_IDS);
    const done = works.filter((_, index) => results[index]?.status === "fulfilled");
    const doneIds = new Set(done.map((work) => work.conversationId));
    const leaving = new Set(rowsAfterResolving(view, rows, doneIds));
    if (leaving.size > 0) {
      list.page.updateItems((items) => items.filter((item) => !leaving.has((item as { id: string }).id)));
    }
    refresh(ids);
    if (done.length === 0) {
      const failure = results.find((result) => result.status === "rejected");
      toast.error(failure?.status === "rejected" ? failure.reason : null);
      return false;
    }
    const title =
      done.length === works.length
        ? tp("inboxTriage.resolved", done.length)
        : t("inboxTriage.resolvedPartly", { done: done.length, total: works.length });
    toast.undoable(title, () => void undo(done));
    return done.length === works.length;
  };

  /** Assigns the row to me (a teammate's stays theirs: the API says so). */
  const takeIt = async (row: InboxRow) => {
    if (row.assigneeUserId === undefined || row.assignmentRevision === undefined) {
      return;
    }
    if (row.assigneeUserId === me.user.id) {
      toast.success(t("inboxTriage.alreadyYours"));
      return;
    }
    setBusyIds(new Set([row.id]));
    try {
      await unwrap(
        api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/assign", {
          params: { path: { business_id: businessId, conversation_id: row.id } },
          body: { assignee_user_id: me.user.id, expected_revision: row.assignmentRevision },
        }),
      );
      toast.success(t("inbox.assign.taken"));
    } catch (error) {
      toast.error(error, { conflict: "inbox.assign.conflict" }, {
        assignment_changed: () => ({ key: "inbox.assign.conflict" }),
        assigned_to_colleague: () => ({ key: "inbox.assign.colleague" }),
      });
    } finally {
      setBusyIds(NO_IDS);
      refresh([row.id]);
    }
  };

  return { resolve, takeIt, busyIds };
}
