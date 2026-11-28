"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { helpArticlePath } from "@/lib/help/helpTopics";
import { businessPath } from "@/lib/navigation";

import { TRANSFER_READINESS_TEXTS, TRANSFER_READINESS_TONES, type TransferReadiness } from "../../_lib/calls";
import { transferTexts } from "../../_lib/transferTexts";

/**
 * Transfers to staff: where calls are put through while the business is
 * open, and the owner's confirmation that those staff were told the voice
 * platform may process the call after the transfer; without it nobody is
 * put through. What the card says depends on the business's country
 * (`transferTexts`): the Italian labour law and the help article with the
 * notice to give staff for a business in Italy only, "another EU country"
 * in the staff number rule for a business in the EU only. The switch
 * itself is the form's.
 */
export function TransferCard({
  readiness,
  phoneNumber,
  confirmedAt,
  switchRow,
}: {
  readiness: TransferReadiness;
  phoneNumber: string | null;
  confirmedAt: number | null;
  switchRow: ReactNode;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const texts = transferTexts(business.country_code);
  return (
    <Card title={t("callSettings.transfers.title")} description={t(texts.description)}>
      <div className="space-y-5">
        {switchRow}
        {confirmedAt !== null ? (
          <p className="text-sm text-ink-muted">{t("callSettings.transfers.confirmedOn", { date: format.date(confirmedAt) })}</p>
        ) : null}
        <Alert tone={TRANSFER_READINESS_TONES[readiness]}>
          <p>{t(TRANSFER_READINESS_TEXTS[readiness])}</p>
          {texts.noticeTemplate ? (
            <p className="mt-1">
              <Link
                href={helpArticlePath(texts.noticeTemplate)}
                className="font-medium text-accent underline underline-offset-2 hover:no-underline"
              >
                {t("callSettings.transfers.noticeTemplate")}
              </Link>
            </p>
          ) : null}
        </Alert>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <div className="min-w-0 text-sm">
            {phoneNumber ? (
              <dl className="flex flex-wrap gap-x-2">
                <dt className="text-ink-muted">{t("callSettings.transfers.number")}</dt>
                <dd dir="ltr" className="font-medium text-ink">
                  {phoneNumber}
                </dd>
              </dl>
            ) : null}
            <p className="mt-0.5 text-ink-muted">{t(texts.numberRule)}</p>
          </div>
          <ButtonLink href={businessPath(business.id, "settings/notifications")} variant="secondary" size="sm">
            {t("callSettings.transfers.openContacts")}
          </ButtonLink>
        </div>
      </div>
    </Card>
  );
}
