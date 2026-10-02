"use client";

import { IconInfo, IconRefresh } from "@/components/icons";
import { Button, Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AssistantVersionSummary } from "@/lib/assistant/versions";

/** The version the chat talks to, a fresh conversation, and what a test conversation does not do. */
export function ChatVersionBar({
  versions,
  versionId,
  isSending,
  versionLabel,
  onStartNew,
}: {
  versions: AssistantVersionSummary[];
  versionId: string | null;
  isSending: boolean;
  versionLabel: (id: string | null, number?: number | null) => string;
  onStartNew: (versionId?: string | null) => void;
}) {
  const { t } = useI18n();
  const selected = versions.find((version) => version.id === versionId);
  return (
    <>
      <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <Field label={t("assistant.chat.version")} className="sm:w-80">
          {(control) => (
            <Select
              {...control}
              value={versionId ?? ""}
              disabled={isSending}
              onChange={(event) => onStartNew(event.target.value)}
            >
              {versions.map((version) => (
                <option key={version.id} value={version.id}>
                  {versionLabel(version.id)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Button variant="secondary" leadingIcon={<IconRefresh className="size-4" aria-hidden />} onClick={() => onStartNew()} disabled={isSending}>
          {t("assistant.chat.newConversation")}
        </Button>
      </div>
      <p className="flex items-start gap-2 border-b border-line bg-surface-muted/50 px-4 py-2.5 text-sm text-ink-muted sm:px-6">
        <IconInfo className="mt-0.5 size-4 shrink-0" aria-hidden />
        {selected?.status === "archived" || selected?.status === "tests_failed"
          ? t("assistant.chat.sandboxNoteRisky", { version: versionLabel(versionId) })
          : t("assistant.chat.sandboxNote")}
      </p>
    </>
  );
}
