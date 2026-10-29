"use client";

/**
 * /admin/partners: the agencies and consultants who bring businesses,
 * with their codes, rates and commissions, and the monthly payouts. Adding
 * a partner, a code, a rate or a pause takes the billing permission (the
 * API checks it; the buttons are hidden without it).
 */

import { useState } from "react";

import type { Schema } from "@/api/types";
import { IconPlus } from "@/components/icons";
import { Badge, Button, Card, ErrorState, LoadingRegion, OverflowMenu, PageHeader, SkeletonCard, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { hasAdminPermission } from "@/lib/adminPermissions";
import { formatMoney, formatNumber } from "@/lib/format";
import { basisPointsToPercent } from "@/lib/referrals/referralLinks";
import type { CurrentUserView } from "@/api/types";

import { useAdminPartners } from "../_lib/useAdminPartners";
import { AddPartnerDialog, CodeDialog, RateDialog } from "./PartnerDialogs";
import { PayoutsCard } from "./PayoutsCard";

type PartnerAdminView = Schema<"PartnerAdminView">;
type Editing = { kind: "rate" | "code"; partner: PartnerAdminView } | null;

export function PartnersScreen({ me }: { me: CurrentUserView }) {
  const { t } = useI18n();
  const toast = useToast();
  const canManage = hasAdminPermission(me, "manage_client_billing");
  const { partners, create, creation, update, change, addCode, codeAddition } = useAdminPartners();
  const [isAdding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Editing>(null);
  const items = partners.data?.items ?? [];

  const onAdd = async (body: Parameters<typeof create>[0]) => {
    if (await create(body)) {
      setAdding(false);
      toast.success(t("adminPartners.added"));
    }
  };
  const onStatus = async (partner: PartnerAdminView) => {
    const status = partner.status === "active" ? "paused" : "active";
    if (await update(partner.partner_id, { status })) {
      toast.success(t(status === "paused" ? "adminPartners.pausedToast" : "adminPartners.resumedToast"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("adminPartners.title")}
        description={t("adminPartners.description")}
        actions={
          canManage ? (
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setAdding(true)}>
              {t("adminPartners.add")}
            </Button>
          ) : undefined
        }
      />
      <div className="space-y-6">
        {partners.error && !partners.data ? (
          <Card>
            <ErrorState error={partners.error} onRetry={partners.reload} />
          </Card>
        ) : !partners.data ? (
          <PartnersSkeleton />
        ) : (
          <Card aria-label={t("adminPartners.title")} padded={false}>
            {items.length === 0 ? (
              <p className="p-5 text-sm text-ink-muted">{t("adminPartners.empty")}</p>
            ) : (
              <ul className="divide-y divide-line">
                {items.map((partner) => (
                  <PartnerRow
                    key={partner.partner_id}
                    partner={partner}
                    canManage={canManage}
                    onStatus={() => void onStatus(partner)}
                    onRate={() => setEditing({ kind: "rate", partner })}
                    onCode={() => setEditing({ kind: "code", partner })}
                  />
                ))}
              </ul>
            )}
          </Card>
        )}
        <PayoutsCard canMarkPaid={canManage} />
        <p className="text-xs text-ink-subtle">{t("adminPartners.legal")}</p>
      </div>

      <AddPartnerDialog open={isAdding} isPending={creation.isPending} error={creation.error} onClose={() => setAdding(false)} onAdd={onAdd} />
      <RateDialog
        open={editing?.kind === "rate"}
        name={editing?.partner.name ?? ""}
        basisPoints={editing?.partner.commission_rate_basis_points ?? 0}
        isPending={change.isPending}
        error={change.error}
        onClose={() => setEditing(null)}
        onSave={async (basisPoints) => {
          if (editing && (await update(editing.partner.partner_id, { commission_rate_basis_points: basisPoints }))) {
            setEditing(null);
            toast.success(t("adminPartners.rateSaved"));
          }
        }}
      />
      <CodeDialog
        open={editing?.kind === "code"}
        name={editing?.partner.name ?? ""}
        isPending={codeAddition.isPending}
        error={codeAddition.error}
        onClose={() => setEditing(null)}
        onAdd={async (code) => {
          if (editing && (await addCode(editing.partner.partner_id, code))) {
            setEditing(null);
            toast.success(t("adminPartners.codeAdded"));
          }
        }}
      />
    </>
  );
}

function PartnerRow({
  partner,
  canManage,
  onStatus,
  onRate,
  onCode,
}: {
  partner: PartnerAdminView;
  canManage: boolean;
  onStatus: () => void;
  onRate: () => void;
  onCode: () => void;
}) {
  const { t, locale } = useI18n();
  const money = (status: "accrued" | "paid") =>
    (partner.totals ?? [])
      .filter((total) => total.status === status && total.amount_minor > 0)
      .map((total) => formatMoney(total.amount_minor, total.currency_code, locale))
      .join(" · ") || "—";
  const rate = formatNumber(basisPointsToPercent(partner.commission_rate_basis_points) / 100, locale, { style: "percent", maximumFractionDigits: 2 });
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 px-5 py-4" data-testid="partner-row">
      <div className="min-w-0 space-y-1">
        <p className="flex flex-wrap items-center gap-2 font-medium text-ink">
          {partner.name}
          <Badge tone={partner.status === "active" ? "success" : "neutral"}>{t(`adminPartners.statuses.${partner.status}`)}</Badge>
        </p>
        <p className="text-xs text-ink-subtle" dir="ltr">
          {partner.phone_number ?? partner.email ?? ""}
        </p>
        <p className="text-sm text-ink-muted">
          {t("adminPartners.columns.rate")}: {rate} · {t("adminPartners.columns.codes")}:{" "}
          <span className="font-mono text-xs">{(partner.codes ?? []).map((code) => code.code).join(", ")}</span>
        </p>
        <p className="text-sm text-ink-muted">
          {t("adminPartners.columns.businesses")}:{" "}
          {t("adminPartners.businessesValue", {
            count: formatNumber(partner.referred_businesses, locale),
            paying: formatNumber(partner.paid_businesses, locale),
          })}{" "}
          · {t("adminPartners.columns.accrued")}: {money("accrued")} · {t("adminPartners.columns.paid")}: {money("paid")}
        </p>
      </div>
      {canManage ? (
        <OverflowMenu
          label={t("adminPartners.actions", { name: partner.name })}
          placement="bottom"
          actions={[
            { key: "status", label: t(partner.status === "active" ? "adminPartners.pause" : "adminPartners.resume"), onSelect: onStatus },
            { key: "rate", label: t("adminPartners.changeRate"), onSelect: onRate },
            { key: "code", label: t("adminPartners.addCode"), onSelect: onCode },
          ]}
        />
      ) : null}
    </li>
  );
}

/** The list while it loads (also the route's loading.tsx). */
export function PartnersSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("adminPartners.loading")}>
      <SkeletonCard lines={5} />
    </LoadingRegion>
  );
}
