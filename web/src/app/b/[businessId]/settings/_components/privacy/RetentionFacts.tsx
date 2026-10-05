"use client";

import { useId } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconInfo } from "@/components/icons";
import { useI18n } from "@/i18n/client";

import { NAMED_PROCESSORS, purgeSummary, type PrivacySettingsView } from "../../_lib/privacySettings";

/**
 * What follows the periods: the sub-processors whose copies go with the
 * platform's own (those this platform uses), the customer's own chat
 * apps, and what the latest nightly cleanup removed.
 */
export function RetentionFacts({ stored }: { stored: PrivacySettingsView }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const processorsId = useId();
  const cleanupId = useId();
  const processors = NAMED_PROCESSORS.filter((processor) => stored.erasure_processors?.includes(processor));
  const lastPurge = stored.last_purge ?? null;
  const summary = lastPurge ? purgeSummary(lastPurge.counts) : null;

  return (
    <div className="grid gap-4 border-t border-line pt-5 md:grid-cols-2">
      <section aria-labelledby={processorsId} className="space-y-2 text-sm">
        <h3 id={processorsId} className="font-semibold text-ink">
          {t("privacyRetention.processorsTitle")}
        </h3>
        {processors.length > 0 ? (
          <>
            <p className="text-ink-muted">{t("privacyRetention.processorsDeleted")}</p>
            <ul className="space-y-1.5">
              {processors.map((processor) => (
                <li key={processor} className="flex gap-2 text-ink">
                  <IconCheckCircle className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                  <span>{t(`privacyRetention.processors.${processor}`)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-ink-muted">{t("privacyRetention.processorsNone")}</p>
        )}
        <p className="flex gap-2 text-xs text-ink-subtle">
          <IconInfo className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>{t("privacyRetention.messagingApps")}</span>
        </p>
      </section>

      <section aria-labelledby={cleanupId} className="space-y-2 text-sm">
        <h3 id={cleanupId} className="font-semibold text-ink">
          {t("privacyRetention.lastCleanupTitle")}
        </h3>
        {lastPurge === null || summary === null ? (
          <p className="text-ink-muted">{t("privacyRetention.noCleanupYet")}</p>
        ) : (
          <div className="space-y-1">
            <p className="text-ink">
              {t("privacyRetention.lastCleanup", { date: format.dateTime(lastPurge.ran_at) })}
              {" · "}
              {summary.total > 0 ? tp("privacyRetention.removed", summary.total) : t("privacyRetention.nothingDue")}
            </p>
            {summary.parts.length > 0 ? (
              <p className="text-ink-muted">
                {summary.parts
                  .map((part) => `${t(`privacyRetention.counts.${part.field}`)}: ${format.number(part.count)}`)
                  .join(" · ")}
              </p>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
