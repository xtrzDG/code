"use client";

/**
 * The business's ready answers as lines that save themselves: a line is
 * saved a moment after the owner stops typing in it (once it has both a
 * question and an answer), when they leave it, and when the page goes
 * away; a removed line is deleted. A suggestion the owner accepts with
 * its answer is saved at once.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useQuery } from "@/api/useQuery";
import type { KnowledgeItemDetails } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { faqRowsFrom, faqSave, savedFaqRow } from "@/lib/profile/faq";
import { newFaqRow, type FaqRow } from "@/lib/wizard/faq";

import { useSaveTracker } from "../SaveTracker";
import { useLineSaves } from "../useLineSaves";
import type { LineSaveStatus } from "../fields/SaveMark";

export function useFaqRows(businessId: string) {
  const { locale } = useI18n();
  const track = useSaveTracker();
  const knowledge = useQuery(
    queryKeys.knowledge.wizardItems(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: businessId }, query: { language: locale, limit: "200" } },
      }),
    { requireFresh: true },
  );
  const [rows, setRows] = useState<FaqRow[] | null>(null);
  const [status, setStatus] = useState<Record<string, LineSaveStatus>>({});
  const sequence = useRef(0);
  const latest = useRef<FaqRow[]>([]);
  // Ids of lines created here, known before the list draws them (a line removed right after it was saved).
  const ids = useRef(new Map<string, string>());
  const toSave = useRef<string[]>([]);

  if (rows === null && knowledge.data) {
    setRows(faqRowsFrom(knowledge.data.items ?? []));
  }
  const shown = rows ?? [];
  useEffect(() => {
    latest.current = shown;
  });

  const saveNow = useCallback(
    async (key: string): Promise<boolean> => {
      const found = latest.current.find((line) => line.key === key);
      const knownId = ids.current.get(key);
      const row = found && knownId && !found.id ? { ...found, id: knownId } : found;
      const plan = row ? faqSave(row) : ({ kind: "none" } as const);
      if (plan.kind === "none") {
        return true;
      }
      if (plan.kind === "invalid") {
        return false;
      }
      setStatus((current) => ({ ...current, [key]: "saving" }));
      const request: Promise<KnowledgeItemDetails> =
        plan.kind === "create"
          ? unwrap(api.POST("/v1/businesses/{business_id}/knowledge", { params: { path: { business_id: businessId } }, body: plan.body }))
          : unwrap(
              api.PATCH("/v1/businesses/{business_id}/knowledge/{item_id}", {
                params: { path: { business_id: businessId, item_id: plan.id } },
                body: plan.body,
              }),
            );
      const ok = await track(
        request.then(
          (item) => {
            ids.current.set(key, item.id);
            setRows((current) => (current ?? []).map((line) => (line.key === key ? savedFaqRow(line, item) : line)));
            return true;
          },
          () => false,
        ),
      );
      setStatus((current) => ({ ...current, [key]: ok ? "saved" : "failed" }));
      return ok;
    },
    [businessId, track],
  );

  const lines = useLineSaves(saveNow, { flushOnLeave: true, keys: () => latest.current.map((row) => row.key) });
  const { save } = lines;

  // Lines added with their answer in the last render are saved once the list holds them.
  useEffect(() => {
    toSave.current.splice(0).forEach((key) => void save(key));
  });

  const update = (key: string, patch: Partial<Pick<FaqRow, "question" | "answer">>) => {
    setRows((current) => (current ?? []).map((row) => (row.key === key ? { ...row, ...patch } : row)));
    lines.later(key);
  };

  /** A new line (empty, or a suggested question with or without its answer); returns its key. */
  const add = (question = "", answer = "") => {
    sequence.current += 1;
    const key = `new-${sequence.current}`;
    setRows((current) => [...(current ?? []), { ...newFaqRow(key), question, answer }]);
    if (question.trim() !== "" && answer.trim() !== "") {
      toSave.current.push(key);
    }
    return key;
  };

  const remove = async (key: string) => {
    await lines.settle(key);
    const id = ids.current.get(key) ?? latest.current.find((row) => row.key === key)?.id ?? null;
    setRows((current) => (current ?? []).filter((row) => row.key !== key));
    if (id) {
      await track(
        unwrap(api.DELETE("/v1/businesses/{business_id}/knowledge/{item_id}", { params: { path: { business_id: businessId, item_id: id } } })).then(
          () => true,
          () => false,
        ),
      );
    }
  };

  return { rows: shown, isLoading: rows === null, error: knowledge.error, reload: knowledge.reload, status, update, add, remove, save };
}

export type FaqRows = ReturnType<typeof useFaqRows>;
