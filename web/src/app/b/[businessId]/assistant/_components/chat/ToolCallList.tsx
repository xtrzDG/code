"use client";

import { IconWrench } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { prettyJson } from "@/lib/assistant/testChat";

import { TOOL_LABELS } from "../../_lib/toolLabels";
import type { ToolCallView } from "../../_lib/chatEntries";

/** The tools the assistant called for one reply, with their input and result (folded). */
export function ToolCallList({ toolCalls }: { toolCalls: ToolCallView[] }) {
  const { t, tp } = useI18n();
  return (
    <details className="w-full max-w-[85%] rounded-xl border border-line">
      <summary className="flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm text-ink-muted hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:outline-focus">
        <IconWrench className="size-4" aria-hidden />
        {tp("assistant.chat.toolCalls", toolCalls.length)}
      </summary>
      <ol className="space-y-3 border-t border-line px-3 py-3">
        {toolCalls.map((call, index) => (
          <li key={index} className="space-y-1.5">
            <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
              {t(TOOL_LABELS[call.tool_name].name)}
              <code className="text-xs font-normal text-ink-subtle">{call.tool_name}</code>
              {call.is_error ? <Badge tone="danger">{t("assistant.chat.toolError")}</Badge> : null}
            </p>
            <JsonPart label={t("assistant.chat.toolInput")} json={call.input_json} />
            <JsonPart label={t("assistant.chat.toolResult")} json={call.result_json} />
          </li>
        ))}
      </ol>
    </details>
  );
}

/** A tool call's input or result; the API sends them to platform admins only. */
function JsonPart({ label, json }: { label: string; json: string | null | undefined }) {
  if (json == null) {
    return null;
  }
  return (
    <>
      <p className="text-xs font-medium text-ink-subtle">{label}</p>
      <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-2 text-xs break-words whitespace-pre-wrap text-ink">
        {prettyJson(json)}
      </pre>
    </>
  );
}
