"use client";

import type { Schema } from "@/api/types";
import { Card } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

type TemplatePreview = Schema<"TextBackTemplatePreview">;

/**
 * The text-back to register as a WhatsApp utility template, in each
 * language of the business: the body to paste into Meta Business Manager
 * (its parameter is the business name) and what a caller reads.
 */
export function TemplateTextCard({ previews }: { previews: readonly TemplatePreview[] }) {
  const { t, locale } = useI18n();
  return (
    <Card title={t("callSettings.template.title")} description={t("callSettings.template.description")}>
      <ul className="space-y-4">
        {previews.map((preview) => (
          <li key={preview.language} className="rounded-xl border border-line p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{languageName(preview.language, locale)}</h3>
              <CopyButton value={preview.template_body} />
            </div>
            <dl className="mt-3 space-y-3 text-sm">
              <div>
                <dt className="text-ink-muted">{t("callSettings.template.body")}</dt>
                <dd className="mt-1">
                  <pre
                    lang={preview.language}
                    dir="auto"
                    className="rounded-lg bg-surface-muted px-3 py-2 font-sans text-sm leading-relaxed whitespace-pre-wrap text-ink [overflow-wrap:anywhere]"
                  >
                    {preview.template_body}
                  </pre>
                </dd>
              </div>
              <div>
                <dt className="text-ink-muted">{t("callSettings.template.example")}</dt>
                <dd lang={preview.language} dir="auto" className="mt-1 text-ink">
                  {preview.example}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </Card>
  );
}
