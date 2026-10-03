"use client";

/**
 * The offer table of the tunnel and how it saves itself: a line is saved
 * when the owner leaves it (a new item, or a change to one), removed lines
 * are deleted, and Continue saves what is left. The niche's examples stay
 * suggestions until the owner gives them a price or edits them. Saves of
 * one line queue behind each other, so a line is never created twice.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useQuery } from "@/api/useQuery";
import type { KnowledgeItemDetails, KnowledgeItemKind, Schema } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { blankOfferRow, editOfferRow, initialOfferRows, offerSave, savedOfferRow, type TunnelOfferRow } from "@/lib/tunnel/offer";

import { useSaveTracker } from "../SaveTracker";

export type RowStatus = "saving" | "saved" | "failed";

export function useOfferRows(businessId: string, examples: readonly Schema<"StarterOfferView">[], currency: string, kind: KnowledgeItemKind) {
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
  const [rows, setRows] = useState<TunnelOfferRow[] | null>(null);
  // After a reload the table waits for items newer than this (ms since epoch).
  const [loadedAfter, setLoadedAfter] = useState(0);
  const [status, setStatus] = useState<Record<string, RowStatus>>({});
  const [showErrors, setShowErrors] = useState(false);
  const sequence = useRef(0);
  const latest = useRef<TunnelOfferRow[]>([]);
  const ids = useRef(new Map<string, string>());
  const queue = useRef(new Map<string, Promise<boolean>>());

  const items = knowledge.data?.items;
  if (rows === null && items && knowledge.updatedAt > loadedAfter) {
    setRows(initialOfferRows(items, examples, currency));
  }
  const shown = rows ?? [];

  useEffect(() => {
    latest.current = shown;
  });

  const update = (key: string, patch: Partial<Pick<TunnelOfferRow, "title" | "price" | "duration">>) =>
    setRows((current) => (current ?? []).map((row) => (row.key === key ? editOfferRow(row, patch) : row)));

  const add = () => {
    sequence.current += 1;
    setRows((current) => [...(current ?? []), blankOfferRow(kind, `new-${sequence.current}`)]);
  };

  const saveNow = useCallback(
    async (key: string): Promise<boolean> => {
      const found = latest.current.find((item) => item.key === key);
      const knownId = ids.current.get(key);
      const row = found && knownId && !found.id ? { ...found, id: knownId } : found;
      const plan = row ? offerSave(row, currency) : ({ kind: "none" } as const);
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
            setRows((current) => (current ?? []).map((line) => (line.key === key ? savedOfferRow(line, item, currency) : line)));
            return true;
          },
          () => false,
        ),
      );
      setStatus((current) => ({ ...current, [key]: ok ? "saved" : "failed" }));
      return ok;
    },
    [businessId, currency, track],
  );

  /** Save one line (after any save of it still running); false when it is not valid yet or failed. */
  const save = useCallback(
    (key: string): Promise<boolean> => {
      const next = (queue.current.get(key) ?? Promise.resolve(true)).then(() => saveNow(key));
      queue.current.set(key, next);
      return next;
    },
    [saveNow],
  );

  const remove = async (key: string) => {
    await queue.current.get(key);
    const id = ids.current.get(key) ?? latest.current.find((item) => item.key === key)?.id ?? null;
    setRows((current) => (current ?? []).filter((item) => item.key !== key));
    if (id) {
      await track(
        unwrap(api.DELETE("/v1/businesses/{business_id}/knowledge/{item_id}", { params: { path: { business_id: businessId, item_id: id } } })).then(
          () => true,
          () => false,
        ),
      );
    }
  };

  /** Save every line; false when one is not valid or failed (the table then shows why). */
  const saveAll = async (): Promise<boolean> => {
    const results = await Promise.all(latest.current.map((row) => save(row.key)));
    const ok = results.every(Boolean);
    setShowErrors(!ok);
    return ok;
  };

  /** Start again from the server (after an import added items). */
  const reload = () => {
    setLoadedAfter(Date.now());
    setRows(null);
    knowledge.reload();
  };

  return { rows: shown, isLoading: rows === null, error: knowledge.error, status, showErrors, update, add, save, remove, saveAll, reload };
}

export type OfferRows = ReturnType<typeof useOfferRows>;
