"use client";

import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import type { CampaignSettingsView } from "../_lib/returnVisitsModel";

/** The message as customers read it, in each language of the business. */
export function CampaignPreviewCard({ previews }: { previews: CampaignSettingsView["previews"] }) {
  const { t, locale } = useI18n();
  return (
    <Card title={t("returnVisits.preview.title")} description={t("returnVisits.preview.description")}>
      <ul className="space-y-3">
        {(previews ?? []).map((preview) => (
          <li key={preview.language} className="rounded-xl border border-line p-4">
            <h3 className="text-sm font-semibold text-ink">{languageName(preview.language, locale)}</h3>
            <p lang={preview.language} dir="auto" className="mt-2 text-sm leading-relaxed whitespace-pre-wrap text-ink [overflow-wrap:anywhere]">
              {preview.text}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
