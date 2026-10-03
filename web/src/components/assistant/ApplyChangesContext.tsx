"use client";

/**
 * "Apply changes" in the daily cabinet, shared by the banner over every
 * page, the Assistant's button and its sheet: the changes customers do
 * not get yet, the staged progress (useStagedApply, the same as the
 * tunnel's launch) and the one sheet that lists the changes and applies
 * them. Owners only: staff see neither the banner nor the button.
 *
 * Once the changes are live the sheet closes and the owner gets a toast
 * naming them ("Your assistant now knows: …"), wherever they are in the
 * cabinet.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type { Query } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useStagedApply, type ApplyChangesView, type StagedApply } from "@/components/setup/launch/useStagedApply";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { summarizeChanges, type PendingChange, type PendingChangesView } from "@/lib/assistant/pendingChanges";

import { ApplyChangesSheet } from "./ApplyChangesSheet";
import { usePendingChanges } from "./usePendingChanges";

export interface ApplyChangesContextValue {
  /** Owners apply changes; for everyone else the rest is empty. */
  canApply: boolean;
  pending: Query<PendingChangesView>;
  apply: StagedApply<ApplyChangesView | null>;
  /** The changes this owner applied from here (named once they are live), or null. */
  applied: PendingChange[] | null;
  /** Starts "Apply changes" with the changes shown now. */
  start: () => Promise<boolean>;
  open: () => void;
}

const ApplyChangesContext = createContext<ApplyChangesContextValue | null>(null);

export function useApplyChanges(): ApplyChangesContextValue {
  const value = useContext(ApplyChangesContext);
  if (!value) {
    throw new Error("useApplyChanges() must be used inside ApplyChangesProvider.");
  }
  return value;
}

/**
 * Once the changes are live: the sheet closes and a toast names them. After
 * any end the changes are read again.
 */
function useOutcome(
  apply: StagedApply<ApplyChangesView | null>,
  applied: PendingChange[] | null,
  reloadPending: () => void,
  close: () => void,
) {
  const translator = useI18n();
  const toast = useToast();
  const previous = useRef(apply.phase);
  useEffect(() => {
    const before = previous.current;
    previous.current = apply.phase;
    if (before !== "running" || apply.phase === "running") {
      return;
    }
    reloadPending();
    if (apply.phase === "live") {
      close();
      toast.success(summarizeChanges(applied ?? [], translator) ?? translator.t("applyChanges.done.title"));
    }
  }, [apply.phase, applied, reloadPending, close, toast, translator]);
}

export function ApplyChangesProvider({ children }: { children: ReactNode }) {
  const { business, isOwner } = useBusiness();
  const pending = usePendingChanges(business.id, isOwner);
  const apply = useStagedApply<ApplyChangesView | null>(business.id, null, { enabled: isOwner });
  const [isOpen, setOpen] = useState(false);
  const [applied, setApplied] = useState<PendingChange[] | null>(null);
  const close = useCallback(() => setOpen(false), []);
  useOutcome(apply, applied, pending.reload, close);

  const changes = pending.data?.changes;
  const { start: startApply } = apply;
  const start = useCallback(async () => {
    setApplied(changes ?? []);
    return startApply();
  }, [changes, startApply]);
  const open = useCallback(() => setOpen(true), []);

  const value = useMemo<ApplyChangesContextValue>(
    () => ({ canApply: isOwner, pending, apply, applied, start, open }),
    [isOwner, pending, apply, applied, start, open],
  );

  return (
    <ApplyChangesContext.Provider value={value}>
      {children}
      {isOwner ? <ApplyChangesSheet open={isOpen} onClose={close} /> : null}
    </ApplyChangesContext.Provider>
  );
}
