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
 * cabinet. An update stopped by one of the owner's checks offers to fix
 * the answer that failed it: "Fix this answer" opens here, over any page,
 * and leads back to "Apply changes".
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import type { Query } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { AnswerFixDialog } from "@/components/teaching/AnswerFixDialog";
import { useStagedApply, type ApplyChangesView, type StagedApply } from "@/components/setup/launch/useStagedApply";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { NamedFailure } from "@/lib/assistant/ownerChecks";
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
  /** "Fix this answer" on the test answer that failed one of the owner's checks. */
  fixAnswer: (failure: NamedFailure) => void;
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

interface AnswerToFix {
  conversationId: string;
  messageId: string;
}

export function ApplyChangesProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const pending = usePendingChanges(business.id, isOwner);
  const apply = useStagedApply<ApplyChangesView | null>(business.id, null, { enabled: isOwner });
  const [isOpen, setOpen] = useState(false);
  const [applied, setApplied] = useState<PendingChange[] | null>(null);
  const [fixing, setFixing] = useState<AnswerToFix | null>(null);
  const close = useCallback(() => setOpen(false), []);
  useOutcome(apply, applied, pending.reload, close);

  const changes = pending.data?.changes;
  const { start: startApply } = apply;
  const start = useCallback(async () => {
    setApplied(changes ?? []);
    return startApply();
  }, [changes, startApply]);
  const open = useCallback(() => setOpen(true), []);
  const fixAnswer = useCallback((failure: NamedFailure) => {
    if (failure.conversationId && failure.answerMessageId) {
      setOpen(false);
      setFixing({ conversationId: failure.conversationId, messageId: failure.answerMessageId });
    }
  }, []);

  const value = useMemo<ApplyChangesContextValue>(
    () => ({ canApply: isOwner, pending, apply, applied, start, open, fixAnswer }),
    [isOwner, pending, apply, applied, start, open, fixAnswer],
  );

  return (
    <ApplyChangesContext.Provider value={value}>
      {children}
      {isOwner ? <ApplyChangesSheet open={isOpen} onClose={close} /> : null}
      {isOwner ? (
        <AnswerFixDialog
          conversationId={fixing?.conversationId ?? ""}
          messageId={fixing?.messageId ?? null}
          onClose={() => setFixing(null)}
          followUp={{ label: t("updates.failed.applyAfterFix"), onClick: open }}
        />
      ) : null}
    </ApplyChangesContext.Provider>
  );
}
