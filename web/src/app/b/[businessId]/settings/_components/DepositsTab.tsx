"use client";

import { DepositPolicyPanel } from "@/components/deposits/DepositPolicyPanel";
import { useDepositSettings } from "@/components/deposits/useDeposits";
import { Card, ErrorState, LoadingRegion, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { DepositChoicesCard } from "./deposits/DepositChoicesCard";
import { PaymentPagesCard } from "./deposits/PaymentPagesCard";

/**
 * Settings → Deposits (owners): whether bookings wait for a deposit, how
 * long a place waits and until when a cancellation is refunded, the
 * owner's own payment pages, and the deposit a banquet request asks. The
 * deposits of tables, rooms, masters and services are set on their cards.
 */
export function DepositsTab() {
  const { t } = useI18n();
  const settings = useDepositSettings();

  if (settings.error && !settings.data) {
    return <ErrorState error={settings.error} onRetry={settings.reload} className="py-6" />;
  }
  if (!settings.data) {
    return (
      <LoadingRegion label={t("common.loading")} className="space-y-6">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
      </LoadingRegion>
    );
  }

  return (
    <div className="space-y-6">
      <DepositChoicesCard stored={settings.data} onSaved={settings.setData} />
      <PaymentPagesCard settings={settings.data} onSaved={settings.setData} />
      <Card title={t("deposits.banquet.title")} description={t("deposits.banquet.description")}>
        <DepositPolicyPanel target={{ target: "banquet" }} heading={t("deposits.policy.title")} linksSettings={false} />
      </Card>
    </div>
  );
}
