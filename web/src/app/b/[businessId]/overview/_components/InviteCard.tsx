"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { InviteLinkPanel } from "@/components/referrals/InviteLinkPanel";
import { useReferralProgram } from "@/components/referrals/useReferralProgram";
import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * "Invite a business — a month free" on the Overview (owners), from the
 * tenth booking: the invitation link to copy, share or show as a QR code,
 * and how many businesses signed up, paid and earned the month. Until
 * then (or when the program cannot be read) it stays out of the way; the
 * account menu has the same invitation at any time.
 */
export function InviteCard() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const { program } = useReferralProgram(business.id);
  const view = program.data;

  if (!view || !view.is_invite_card_due) {
    return null;
  }
  return (
    <Card aria-label={t("referrals.title")} title={t("referrals.title")} description={t("referrals.lead")} data-testid="invite-card">
      <div className="space-y-3">
        <InviteLinkPanel view={view} formatCount={format.number} />
        <p className="text-xs text-ink-subtle">{t("referrals.terms")}</p>
      </div>
    </Card>
  );
}
