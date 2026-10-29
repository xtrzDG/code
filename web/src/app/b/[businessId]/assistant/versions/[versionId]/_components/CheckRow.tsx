"use client";

import type { ReactNode } from "react";

import { IconAlert, IconCheckCircle, IconClock, IconXCircle } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import type { CheckState } from "@/lib/assistant/goLive";

const STATE_LABELS: Record<CheckState, MessageKey> = {
  ok: "assistant.checklist.state.ok",
  missing: "assistant.checklist.state.missing",
  pending: "assistant.checklist.state.pending",
  warning: "assistant.checklist.state.warning",
};

function StateIcon({ state }: { state: CheckState }) {
  if (state === "ok") {
    return <IconCheckCircle className="size-5 text-success" aria-hidden />;
  }
  if (state === "pending") {
    return <IconClock className="size-5 text-info" aria-hidden />;
  }
  if (state === "warning") {
    return <IconAlert className="size-5 text-warning" aria-hidden />;
  }
  return <IconXCircle className="size-5 text-danger" aria-hidden />;
}

/** One launch condition: its state icon, title, what it says and how to fix it. */
export function CheckRow({ state, title, detail, action }: { state: CheckState; title: string; detail?: ReactNode; action?: ReactNode }) {
  const { t } = useI18n();
  return (
    <li className="flex items-start gap-3 py-3">
      <span className="mt-0.5 shrink-0">
        <StateIcon state={state} />
      </span>
      <div className="min-w-0 flex-1 sm:flex sm:items-center sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">
            {title}
            <span className="sr-only">: {t(STATE_LABELS[state])}</span>
          </p>
          {detail ? <div className="mt-0.5 text-sm text-ink-muted">{detail}</div> : null}
        </div>
        {action ? <div className="mt-1.5 sm:mt-0 sm:shrink-0">{action}</div> : null}
      </div>
    </li>
  );
}
