"use client";

import { Alert, Button, Card, LoadingBlock, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AssistantVersionSummary } from "@/lib/assistant/versions";

import { useTestChat } from "../../_lib/useTestChat";
import { ChatComposer } from "./ChatComposer";
import { ChatEmpty } from "./ChatEmpty";
import { ChatLine } from "./ChatLine";
import { ChatVersionBar } from "./ChatVersionBar";

/** The test conversation with one version: its log, a handoff notice and the message box. */
export function TestChat({ versions, initialVersionId }: { versions: AssistantVersionSummary[]; initialVersionId: string | null }) {
  const { t } = useI18n();
  const { scroller, input, session, entries, isRestoring, isHandedOff, isSending, text, setText, startNew, deliver, submit, onKeyDown, versionLabel } =
    useTestChat(versions, initialVersionId);

  return (
    <Card padded={false}>
      <ChatVersionBar
        versions={versions}
        versionId={session.versionId}
        isSending={isSending}
        versionLabel={versionLabel}
        onStartNew={startNew}
      />

      <div
        ref={scroller}
        role="log"
        aria-live="polite"
        aria-label={t("assistant.chat.logLabel")}
        className="h-[min(60vh,36rem)] min-h-72 space-y-4 overflow-y-auto px-4 py-5 sm:px-6"
      >
        {isRestoring ? (
          <LoadingBlock label={t("common.loading")} />
        ) : entries.length === 0 ? (
          <ChatEmpty onSuggest={(message) => void deliver(message)} />
        ) : (
          entries.map((entry) => (
            <ChatLine
              key={entry.key}
              entry={entry}
              versionLabel={versionLabel}
              onRetry={(message, key) => void deliver(message, key)}
              isSending={isSending}
            />
          ))
        )}
        {isSending ? (
          <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
            <Spinner size="sm" /> {t("assistant.chat.typing")}
          </div>
        ) : null}
      </div>

      {isHandedOff ? (
        <Alert
          tone="info"
          className="mx-4 mb-3 sm:mx-6"
          title={t("assistant.chat.handedOffTitle")}
          action={
            <Button size="sm" variant="secondary" onClick={() => startNew()}>
              {t("assistant.chat.newConversation")}
            </Button>
          }
        >
          {t("assistant.chat.handedOffDescription")}
        </Alert>
      ) : null}

      <ChatComposer input={input} text={text} isSending={isSending} onChange={setText} onSubmit={submit} onKeyDown={onKeyDown} />
    </Card>
  );
}
