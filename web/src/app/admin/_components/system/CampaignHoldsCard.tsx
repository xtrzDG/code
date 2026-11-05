"use client";

import Link from "next/link";
import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  ErrorState,
  TBody,
  THead,
  Td,
  Th,
  Tr,
} from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import { adminClientPath } from "@/lib/navigation";

import { type CampaignHold, useCampaignHolds } from "../../_lib/useCampaignHolds";
import { ActionDialog } from "../client/actions/ActionDialog";
import { ScrollingTable } from "../metrics/ScrollingTable";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The return-visit campaigns the hourly job held over their opt-out rate
 * (ABUSE-05), the longest held first: the client, since when, and how many
 * of the customers it wrote to opted out. SUPER admins (`canRelease`)
 * release one with the reason the client's audit log keeps. Shown only
 * while a campaign is held; hidden from an admin whose role does not see
 * operations.
 */
export function CampaignHoldsCard({ canRelease }: { canRelease: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const { holds, releaseHold, isReleasing, releaseError } = useCampaignHolds();
  const [releasing, setReleasing] = useState<CampaignHold | null>(null);
  const title = t("platformBrakes.campaignHolds.title");
  const items = holds.data?.items;

  // Nothing to look at, nothing shown: the card appears once a campaign is
  // held (or the list cannot be read).
  if (holds.error?.status === 403 || (!holds.error && !items?.length)) {
    return null;
  }

  const confirm = async (reason: string) => {
    if (!releasing) return;
    if (await releaseHold(releasing.business_id, reason)) {
      setReleasing(null);
      toast.success(t("platformBrakes.campaignHolds.released"));
    }
  };

  return (
    <Card
      aria-label={title}
      title={title}
      description={t("platformBrakes.campaignHolds.description")}
      actions={
        items && items.length > 0 ? (
          <Badge tone="warning">{items.length}</Badge>
        ) : undefined
      }
    >
      {holds.error && !items ? (
        <ErrorState error={holds.error} onRetry={holds.reload} />
      ) : (
        <HoldsTable
          holds={items ?? []}
          title={title}
          onRelease={canRelease ? setReleasing : undefined}
        />
      )}
      <ActionDialog
        key={releasing?.business_id ?? "closed"}
        open={releasing !== null}
        title={t("platformBrakes.campaignHolds.releaseTitle")}
        description={t("platformBrakes.campaignHolds.releaseDescription")}
        confirmLabel={t("platformBrakes.campaignHolds.release")}
        isPending={isReleasing}
        error={releaseError}
        onClose={() => setReleasing(null)}
        onConfirm={confirm}
      />
    </Card>
  );
}

function HoldsTable({
  holds,
  title,
  onRelease,
}: {
  holds: CampaignHold[];
  title: string;
  onRelease?: (hold: CampaignHold) => void;
}) {
  const { t } = useI18n();
  const format = useSystemFormat();
  return (
    <ScrollingTable caption={title}>
      <THead>
        <Tr>
          <Th>{t("platformBrakes.campaignHolds.client")}</Th>
          <Th>{t("platformBrakes.campaignHolds.heldSince")}</Th>
          <Th>{t("platformBrakes.campaignHolds.optedOut")}</Th>
          {onRelease ? (
            <Th>
              <span className="sr-only">
                {t("platformBrakes.campaignHolds.release")}
              </span>
            </Th>
          ) : null}
        </Tr>
      </THead>
      <TBody>
        {holds.map((hold) => (
          <Tr key={hold.business_id}>
            <Td>
              <Link
                className="text-accent hover:underline"
                href={adminClientPath(hold.business_id)}
              >
                {hold.business_id}
              </Link>
            </Td>
            <Td>{format.when(hold.held_at)}</Td>
            <Td>
              {t("platformBrakes.campaignHolds.optedOutOf", {
                optedOut: format.number(hold.opted_out),
                sent: format.number(hold.sent),
              })}
            </Td>
            {onRelease ? (
              <Td>
                <Button variant="secondary" onClick={() => onRelease(hold)}>
                  {t("platformBrakes.campaignHolds.release")}
                </Button>
              </Td>
            ) : null}
          </Tr>
        ))}
      </TBody>
    </ScrollingTable>
  );
}
