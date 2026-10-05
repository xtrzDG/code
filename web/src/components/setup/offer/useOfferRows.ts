"use client";

/**
 * The offer table of the tunnel and how it saves itself: a line is saved
 * when the owner leaves it (a new item, or a change to one), removed lines
 * are deleted, and Continue saves what is left. The niche's examples stay
 * suggestions until the owner gives them a price or edits them; one the
 * owner saved as their own line or removed is remembered (offerMemory), so
 * a revisit does not offer it again. Saves of one line queue behind each
 * other, so a line is never created twice.
 *
 * The examples show only while nothing is on offer yet and the step was
 * never finished (initialOfferRows). In the edit mode (Assistant →
 * Business profile) a change to a saved line is also saved a
 * moment after the typing stops, lines pasted from a spreadsheet are added
 * and saved at once, and what is left unsaved goes when the page does.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useQuery } from "@/api/useQuery";
import type { KnowledgeItemDetails, KnowledgeItemKind, Schema } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { blankOfferRow, editOfferRow, initialOfferRows, offerSave, pastedOfferRows, savedOfferRow, type TunnelOfferRow } from "@/lib/tunnel/offer";
import { browserStorage, exampleKeyOf, readDoneExamples, rememberDoneExample } from "@/lib/tunnel/offerMemory";
import type { PastedOffer } from "@/lib/tunnel/offerPaste";

import type { LineSaveStatus } from "../fields/SaveMark";
import { useSaveTracker } from "../SaveTracker";
import type { StepMode } from "../stepMode";
import { useLineSaves } from "../useLineSaves";

export type RowStatus = LineSaveStatus;

export type OfferRowPatch = Partial<Pick<TunnelOfferRow, "title" | "price" | "duration" | "kind">>;

export function useOfferRows(
  businessId: string,
  examples: readonly Schema<"StarterOfferView">[],
  currency: string,
  kind: KnowledgeItemKind,
  mode: StepMode = "tunnel",
  isStepCompleted = false,
) {
  const { locale } = useI18n();
  const track = useSaveTracker();
  const isEdit = mode === "edit";
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
  const toSave = useRef<string[]>([]);

  const items = knowledge.data?.items;
  if (rows === null && items && knowledge.updatedAt > loadedAfter) {
    setRows(initialOfferRows(items, examples, currency, { done: readDoneExamples(browserStorage(), businessId), isStepCompleted }));
  }
  const shown = rows ?? [];

  useEffect(() => {
    latest.current = shown;
  });

  /** An example the owner replaced with their own line or removed: not offered again. */
  const markDone = useCallback(
    (key: string) => {
      const example = exampleKeyOf(key);
      if (example) {
        rememberDoneExample(browserStorage(), businessId, example);
      }
    },
    [businessId],
  );

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
        // The edit mode has no Continue to show the problems on: the line says so itself.
        if (isEdit) {
          setStatus((current) => ({ ...current, [key]: "failed" }));
        }
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
            markDone(key);
            setRows((current) => (current ?? []).map((line) => (line.key === key ? savedOfferRow(line, item, currency) : line)));
            return true;
          },
          () => false,
        ),
      );
      setStatus((current) => ({ ...current, [key]: ok ? "saved" : "failed" }));
      return ok;
    },
    [businessId, currency, isEdit, markDone, track],
  );

  // The edit mode has no Continue: leaving the page saves what is not saved yet.
  const lines = useLineSaves(saveNow, { flushOnLeave: isEdit, keys: () => latest.current.map((row) => row.key) });
  const { save } = lines;

  // Lines added in the last render (pasted ones) are saved once the table holds them.
  useEffect(() => {
    const keys = toSave.current.splice(0);
    keys.forEach((key) => void save(key));
  });

  const update = (key: string, patch: OfferRowPatch) => {
    setRows((current) => (current ?? []).map((row) => (row.key === key ? editOfferRow(row, patch) : row)));
    // A change to a saved line is saved a moment later in the edit mode; a new line when the owner leaves it.
    if (isEdit && (ids.current.has(key) || latest.current.some((row) => row.key === key && row.id !== null))) {
      lines.later(key);
    }
  };

  const add = () => {
    sequence.current += 1;
    setRows((current) => [...(current ?? []), blankOfferRow(kind, `new-${sequence.current}`)]);
  };

  /** Lines pasted from a spreadsheet: they replace the empty line they were pasted into, the rest follow. */
  const paste = (pasted: readonly PastedOffer[], intoKey: string) => {
    const base = sequence.current;
    sequence.current += pasted.length;
    const added = pastedOfferRows(pasted, kind, (index) => `new-${base + index + 1}`);
    setRows((current) => {
      const list = current ?? [];
      const target = list.findIndex((row) => row.key === intoKey && row.id === null && row.title.trim() === "" && row.price.trim() === "");
      return target >= 0 ? [...list.slice(0, target), ...added, ...list.slice(target + 1)] : [...list, ...added];
    });
    toSave.current.push(...added.map((row) => row.key));
    return added.length;
  };

  const remove = async (key: string) => {
    await lines.settle(key);
    const id = ids.current.get(key) ?? latest.current.find((item) => item.key === key)?.id ?? null;
    setRows((current) => (current ?? []).filter((item) => item.key !== key));
    markDone(key);
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

  return { rows: shown, isLoading: rows === null, error: knowledge.error, status, showErrors, update, add, paste, save, remove, saveAll, reload };
}

export type OfferRows = ReturnType<typeof useOfferRows>;
