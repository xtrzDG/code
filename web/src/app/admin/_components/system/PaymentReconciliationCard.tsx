"use client";

import Link from "next/link";

import { IconCheckCircle } from "@/components/icons";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  SkeletonText,
  TBody,
  THead,
  Td,
  Th,
  Tr,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { adminClientPath } from "@/lib/navigation";

import {
  hasMismatches,
  type PaymentReconciliation,
} from "../../_lib/platformBrakes";
import { usePaymentReconciliation } from "../../_lib/usePlatformBrakes";
import { ScrollingTable } from "../metrics/ScrollingTable";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The latest daily reconciliation of the platform's payments with Flitt and
 * Stripe: when it ran, how many payments it compared, and each payment whose
 * status at the provider differs from the platform's (no card data). Only
 * for admins who see money (SUPER, BILLING); hidden from the others.
 */
export function PaymentReconciliationCard() {
  const { t } = useI18n();
  const reconciliation = usePaymentReconciliation();
  const title = t("platformBrakes.reconciliation.title");
  const data = reconciliation.data;

  if (reconciliation.error?.status === 403) {
    return null;
  }

  return (
    <Card
      aria-label={title}
      title={title}
      description={t("platformBrakes.reconciliation.description")}
      actions={
        data && hasMismatches(data) ? (
          <Badge tone="danger">
            {t("platformBrakes.reconciliation.differs")}
          </Badge>
        ) : undefined
      }
    >
      {reconciliation.error && !data ? (
        <ErrorState
          error={reconciliation.error}
          onRetry={reconciliation.reload}
        />
      ) : !data ? (
        <SkeletonText lines={2} />
      ) : (
        <ReconciliationResult reconciliation={data} title={title} />
      )}
    </Card>
  );
}

function ReconciliationResult({
  reconciliation,
  title,
}: {
  reconciliation: PaymentReconciliation;
  title: string;
}) {
  const { t } = useI18n();
  const format = useSystemFormat();
  if (!reconciliation.ran_at) {
    return (
      <p className="text-sm text-ink-muted">
        {t("platformBrakes.reconciliation.notYet")}
      </p>
    );
  }

  const summary = t("platformBrakes.reconciliation.summary", {
    time: format.when(reconciliation.ran_at),
    checked: format.number(reconciliation.checked_count),
    unreadable: format.number(reconciliation.unreadable_count),
  });
  if (!hasMismatches(reconciliation)) {
    return (
      <EmptyState
        icon={<IconCheckCircle className="size-6 text-success" />}
        title={t("platformBrakes.reconciliation.allMatch")}
        description={summary}
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">{summary}</p>
      <ScrollingTable caption={title}>
        <THead>
          <Tr>
            <Th>{t("platformBrakes.reconciliation.client")}</Th>
            <Th>{t("platformBrakes.reconciliation.provider")}</Th>
            <Th>{t("platformBrakes.reconciliation.recorded")}</Th>
            <Th>{t("platformBrakes.reconciliation.atProvider")}</Th>
            <Th>{t("platformBrakes.reconciliation.kind")}</Th>
          </Tr>
        </THead>
        <TBody>
          {reconciliation.mismatches.map((mismatch) => (
            <Tr key={mismatch.payment_order_id}>
              <Td>
                <Link
                  className="text-accent hover:underline"
                  href={adminClientPath(mismatch.business_id)}
                >
                  {mismatch.business_name ?? mismatch.business_id}
                </Link>
              </Td>
              <Td>
                {t(
                  `platformBrakes.reconciliation.providers.${mismatch.provider}`,
                )}
              </Td>
              <Td>
                {t(
                  `platformBrakes.reconciliation.statuses.${mismatch.recorded_status}`,
                )}
              </Td>
              <Td>
                {t(
                  `platformBrakes.reconciliation.statuses.${mismatch.provider_status}`,
                )}
              </Td>
              <Td>
                {t(`platformBrakes.reconciliation.kinds.${mismatch.kind}`)}
              </Td>
            </Tr>
          ))}
        </TBody>
      </ScrollingTable>
    </div>
  );
}
