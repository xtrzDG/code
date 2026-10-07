"use client";

import { Button, ErrorState, LoadingRegion, Modal, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { InviteLinkPanel } from "./InviteLinkPanel";
import { useReferralProgram } from "./useReferralProgram";

/** "Invite a business — a month free" from the account menu (owners). */
export function InviteDialog({ businessId, open, onClose }: { businessId: string; open: boolean; onClose: () => void }) {
  const { t, locale } = useI18n();
  const { program } = useReferralProgram(businessId, { enabled: open });
  const view = program.data;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("referrals.title")}
      description={t("referrals.lead")}
      footer={
        <Button variant="secondary" onClick={onClose}>
          {t("referrals.close")}
        </Button>
      }
    >
      {program.error && !view ? (
        <ErrorState error={program.error} onRetry={program.reload} />
      ) : !view ? (
        <LoadingRegion label={t("referrals.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : (
        <div className="space-y-3">
          <InviteLinkPanel view={view} formatCount={(value) => formatNumber(value, locale)} />
          <p className="text-xs text-ink-subtle">{t("referrals.terms")}</p>
        </div>
      )}
    </Modal>
  );
}
