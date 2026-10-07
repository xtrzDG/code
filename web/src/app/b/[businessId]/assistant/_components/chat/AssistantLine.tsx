"use client";

import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { ChatEntry } from "../../_lib/chatEntries";
import { ReplyChoices } from "./ReplyChoices";
import { ToolCallList } from "./ToolCallList";

/**
 * One answer of the assistant: the version that gave it, the options it
 * offered (buttons to tap while it is the last answer, as in a messenger),
 * what it did (badges) and the tools it called.
 */
export function AssistantLine({
  entry,
  answerLabel,
  onChoose,
  isSending = false,
}: {
  entry: Extract<ChatEntry, { kind: "assistant" }>;
  answerLabel: (versionId: string | null, number?: number | null) => string;
  /** Set while these options can still be tapped: sends the label as the customer's message. */
  onChoose?: ((label: string) => void) | null;
  isSending?: boolean;
}) {
  const { t, tp } = useI18n();
  const reply = entry.reply;
  const toolCalls = entry.toolCalls ?? [];
  const badges: { tone: "warning" | "info" | "success"; label: string }[] = [];
  if (reply?.guard_verdict === "rewritten") {
    badges.push({ tone: "warning", label: t("assistant.chat.guardRewritten") });
  }
  if (reply?.guard_verdict === "handed_off") {
    badges.push({ tone: "warning", label: t("assistant.chat.guardHandedOff") });
  }
  if ((reply?.created_booking_ids ?? []).length > 0) {
    badges.push({ tone: "success", label: tp("assistant.chat.bookingsCreated", (reply?.created_booking_ids ?? []).length) });
  }
  if ((reply?.created_lead_ids ?? []).length > 0) {
    badges.push({ tone: "success", label: tp("assistant.chat.leadsCreated", (reply?.created_lead_ids ?? []).length) });
  }
  if ((reply?.created_handoff_ids ?? []).length > 0 || reply?.is_handed_off) {
    badges.push({ tone: "info", label: t("assistant.chat.handedOff") });
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <p className="mb-0.5 text-xs font-medium text-ink-subtle">
        {t("assistant.authors.assistant")}
        {entry.versionId ? ` · ${answerLabel(entry.versionId, entry.versionNumber)}` : ""}
      </p>
      <div className="max-w-[85%] rounded-2xl rounded-es-md bg-surface-muted px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-ink" dir="auto" data-user-content>
        {entry.text}
      </div>
      {(entry.choices ?? []).length > 0 ? (
        <ReplyChoices choices={entry.choices ?? []} onChoose={onChoose ?? null} isSending={isSending} />
      ) : null}
      {badges.length > 0 ? (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {badges.map((badge) => (
            <Badge key={badge.label} tone={badge.tone}>
              {badge.label}
            </Badge>
          ))}
        </div>
      ) : null}
      {toolCalls.length > 0 ? <ToolCallList toolCalls={toolCalls} /> : null}
    </div>
  );
}
