"use client";

import { IconWrench } from "@/components/content/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { prettyJson } from "@/lib/assistant/testChat";

import { TOOL_LABELS } from "../../versions/[versionId]/VersionDetailScreen";
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
            <p className="text-xs font-medium text-ink-subtle">{t("assistant.chat.toolInput")}</p>
            <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-2 text-xs break-words whitespace-pre-wrap text-ink">
              {prettyJson(call.input_json)}
            </pre>
            <p className="text-xs font-medium text-ink-subtle">{t("assistant.chat.toolResult")}</p>
            <pre className="max-h-48 overflow-auto rounded-lg bg-surface-muted p-2 text-xs break-words whitespace-pre-wrap text-ink">
              {prettyJson(call.result_json)}
            </pre>
          </li>
        ))}
      </ol>
    </details>
  );
}
