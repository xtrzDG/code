"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { Card, ErrorState, LoadingBlock } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

/** The website chat's embed code with a copy button and three steps. */
export function WidgetSnippetCard() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const snippet = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/channels/web/snippet", {
        params: { path: { business_id: business.id } },
      }),
    [business.id],
  );

  return (
    <Card
      title={t("channels.widget.title")}
      description={t("channels.widget.description")}
      actions={snippet.data ? <CopyButton value={snippet.data.snippet} label={t("channels.widget.copyCode")} /> : undefined}
    >
      {snippet.error && !snippet.data ? (
        <ErrorState error={snippet.error} onRetry={snippet.reload} className="py-6" />
      ) : !snippet.data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-24" />
      ) : (
        <div className="space-y-5">
          <figure className="space-y-2">
            <figcaption id="widget-snippet-label" className="text-sm font-medium text-ink">
              {t("channels.widget.codeLabel")}
            </figcaption>
            <pre
              aria-labelledby="widget-snippet-label"
              dir="ltr"
              tabIndex={0}
              className="overflow-x-auto rounded-xl border border-line bg-surface-muted px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all text-ink sm:text-sm"
            >
              <code>{snippet.data.snippet}</code>
            </pre>
          </figure>
          <ol className="grid gap-3 text-sm text-ink-muted sm:grid-cols-3">
            {(["channels.widget.step1", "channels.widget.step2", "channels.widget.step3"] as const).map((step, index) => (
              <li key={step} className="flex gap-3 rounded-xl bg-surface-muted/60 p-3">
                <span
                  className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent"
                  aria-hidden
                >
                  {index + 1}
                </span>
                <span>{t(step)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}
