"use client";

/**
 * The customer's consent to marketing messages (the campaign's invitations
 * back, recalls and pre-arrival notes): what is recorded, where and when,
 * and the team's record of a consent the customer gave or took back in
 * person. Recording asks first and shows the wording the customer agrees
 * to; taking it back does not. While messages to the customer are stopped
 * (STOP, the suppression list, a block) the card never says "agreed", but
 * a consent still recorded can be taken back.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Button, Card, ConfirmDialog, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { namingSentence, withCard, type CustomerDetail, type CustomerNaming } from "../../_lib/customerModel";

export function MarketingConsentCard({ detail, naming }: { detail: Query<CustomerDetail>; naming: CustomerNaming }) {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [isAsking, setAsking] = useState(false);
  const data = detail.data;
  const contactId = data?.contact.id ?? "";

  const record = useMutation(
    (isGiven: boolean) =>
      api.PATCH("/v1/businesses/{business_id}/contacts/{contact_id}/card", {
        params: { path: { business_id: business.id, contact_id: contactId } },
        body: { marketing_consent: isGiven },
      }),
    { errorToast: false, stale: [queryKeys.customers.all(business.id)] },
  );

  if (!data || data.contact.erased_at) {
    return null;
  }
  const consent = data.marketing_consent ?? { status: "not_given" as const };
  // Recorded and not taken back: also while messages are stopped (a block
  // lifted later would bring it back), so the team can still record that
  // the customer took it back.
  const isActive =
    consent.status === "agreed" || (consent.status === "stopped" && Boolean(consent.given_at) && !consent.withdrawn_at);

  const change = async (isGiven: boolean) => {
    const result = await record.run(isGiven);
    if (!result.ok) {
      if (!isGiven) {
        toast.error(result.error);
      }
      return;
    }
    detail.setData((current) => (current ? withCard(current, result.data) : current));
    setAsking(false);
    toast.success(namingSentence(t(isGiven ? "customers.consent.recorded" : "customers.consent.takenBack"), naming));
  };

  const details: string[] = (
    consent.status === "agreed"
      ? [
          consent.given_at ? t("customers.consent.agreed", { date: format.date(consent.given_at) }) : null,
          consent.source ? t(`customers.consent.sources.${consent.source}`) : null,
          consent.text_version ? t("customers.consent.version", { version: consent.text_version }) : null,
        ]
      : consent.status === "withdrawn"
        ? [
            consent.withdrawn_at ? t("customers.consent.withdrawn", { date: format.date(consent.withdrawn_at) }) : null,
            consent.withdrawal ? t(`customers.consent.withdrawals.${consent.withdrawal}`) : null,
          ]
        : []
  ).filter((line): line is string => line !== null);

  return (
    <Card title={t("customers.consent.title")} description={t("customers.consent.description")}>
      <div className="space-y-3" data-testid="marketing-consent-card">
        {consent.status === "stopped" ? (
          <Alert tone="warning">{t("customers.consent.stopped")}</Alert>
        ) : consent.status === "not_given" ? (
          <p className="text-sm text-ink-muted">{t("customers.consent.notGiven")}</p>
        ) : (
          <ul className="space-y-1 text-sm text-ink-muted">
            {details.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
        {isActive ? (
          <Button variant="secondary" isLoading={record.isPending} onClick={() => void change(false)}>
            {t("customers.consent.withdraw")}
          </Button>
        ) : consent.status !== "stopped" ? (
          <Button variant="secondary" onClick={() => setAsking(true)}>
            {t("customers.consent.record")}
          </Button>
        ) : null}
      </div>
      <ConfirmDialog
        open={isAsking}
        onClose={() => setAsking(false)}
        onConfirm={() => change(true)}
        isPending={record.isPending}
        error={record.error}
        title={<UserSentence {...namingSentence(t("customers.consent.recordTitle"), naming)} />}
        confirmLabel={t("customers.consent.confirm")}
      >
        <p>{t("customers.consent.recordBody")}</p>
        <p className="mt-2 text-ink">
          <UserSentence text={t("customers.consent.wording")} values={{ business: business.name }} />
        </p>
      </ConfirmDialog>
    </Card>
  );
}
