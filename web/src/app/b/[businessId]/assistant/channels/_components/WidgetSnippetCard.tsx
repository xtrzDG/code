"use client";

import type { Query } from "@/api/useQuery";
import type { Schema } from "@/api/types";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

/**
 * The website chat's embed code, as it must be pasted: one block that
 * scrolls sideways and never breaks a line inside a tag (`</script>`), with
 * its Copy button right on it; then three steps.
 */
export function WidgetSnippetCard({ snippet }: { snippet: Query<Schema<"WidgetSnippetView">> }) {
  const { t } = useI18n();

  return (
    <Card title={t("channels.widget.title")} description={t("channels.widget.description")}>
      {snippet.error && !snippet.data ? (
        <ErrorState error={snippet.error} onRetry={snippet.reload} className="py-6" />
      ) : !snippet.data ? (
        <LoadingRegion label={t("common.loading")} className="py-1"><SkeletonText lines={4} /></LoadingRegion>
      ) : (
        <div className="space-y-5">
          <figure className="overflow-hidden rounded-xl border border-line bg-surface-muted">
            <figcaption className="flex items-center justify-between gap-3 border-b border-line py-1.5 ps-4 pe-1.5">
              <span id="widget-snippet-label" className="text-sm font-medium text-ink">
                {t("channels.widget.codeLabel")}
              </span>
              <CopyButton value={snippet.data.snippet} label={t("channels.widget.copyCode")} />
            </figcaption>
            <pre
              aria-labelledby="widget-snippet-label"
              dir="ltr"
              tabIndex={0}
              data-widget-snippet=""
              className="overflow-x-auto px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre text-ink focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus sm:text-sm"
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
