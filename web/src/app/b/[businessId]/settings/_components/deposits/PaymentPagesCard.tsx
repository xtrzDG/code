"use client";

import { useState } from "react";

import { defaultPageBody } from "@/components/deposits/depositSettingsModel";
import type { DepositSettingsView, PaymentLinkView } from "@/components/deposits/depositModel";
import { useDepositSettingsActions } from "@/components/deposits/useDeposits";
import { IconPlus, IconTrash } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { PaymentPageForm } from "./PaymentPageForm";

/**
 * The owner's payment pages: each with its name, the address as it is
 * shown (a key in it hidden), whether it fills in the amount, and which one
 * deposits use by default; a page is added below and removed after asking.
 */
export function PaymentPagesCard({
  settings,
  onSaved,
}: {
  settings: DepositSettingsView;
  onSaved: (settings: DepositSettingsView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const actions = useDepositSettingsActions();
  const links = settings.payment_links ?? [];
  const [isAdding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<PaymentLinkView | null>(null);
  const showsForm = isAdding || links.length === 0;

  const makeDefault = async (link: PaymentLinkView) => {
    const result = await actions.save.run(defaultPageBody(settings, link.id));
    if (result.ok) {
      onSaved(result.data);
      toast.success(t("deposits.pages.defaultSet"));
    } else {
      toast.error(result.error);
    }
  };
  const remove = async () => {
    if (!removing) {
      return;
    }
    const result = await actions.removePage.run(removing.id);
    if (result.ok) {
      setRemoving(null);
      toast.success(t("deposits.pages.removed"));
    }
  };

  return (
    <Card
      title={t("deposits.pages.title")}
      description={t("deposits.pages.description")}
      actions={
        links.length > 0 && !isAdding ? (
          <Button size="sm" variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setAdding(true)}>
            {t("deposits.pages.add")}
          </Button>
        ) : null
      }
    >
      <div className="space-y-5">
        {links.length === 0 ? (
          <div className="space-y-1">
            <p className="text-sm font-medium text-ink">{t("deposits.pages.empty")}</p>
            <p className="text-sm text-ink-muted">{t("deposits.pages.emptyDescription")}</p>
          </div>
        ) : (
          <ul className="divide-y divide-line rounded-xl border border-line">
            {links.map((link) => {
              const isDefault = link.id === settings.default_payment_link_id;
              return (
                <li key={link.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-ink" dir="auto" data-user-content>
                        {link.label}
                      </p>
                      {isDefault ? <Badge tone="accent">{t("deposits.pages.default")}</Badge> : null}
                      <Badge>{t(link.kind === "template" ? "deposits.pages.kinds.template" : "deposits.pages.kinds.static")}</Badge>
                      {link.is_sealed ? <Badge tone="neutral">{t("deposits.pages.sealed")}</Badge> : null}
                    </div>
                    <p className="text-sm break-all text-ink-muted" dir="ltr" data-user-content>
                      {link.preview}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-1">
                    {!isDefault && link.kind === "template" ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={actions.save.isPending}
                        title={t("deposits.pages.defaultHint")}
                        onClick={() => void makeDefault(link)}
                      >
                        {t("deposits.pages.makeDefault")}
                      </Button>
                    ) : null}
                    <Button
                      size="sm"
                      variant="danger-ghost"
                      leadingIcon={<IconTrash className="size-4" aria-hidden />}
                      aria-label={t("deposits.pages.removeLabel", { label: link.label })}
                      onClick={() => setRemoving(link)}
                    >
                      {t("common.delete")}
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {links.some((link) => link.id === settings.default_payment_link_id) ? (
          <p className="text-sm text-ink-muted">{t("deposits.pages.defaultHint")}</p>
        ) : null}
        {showsForm ? (
          <PaymentPageForm
            onAdded={(saved) => {
              onSaved(saved);
              setAdding(false);
            }}
            onCancel={links.length > 0 ? () => setAdding(false) : undefined}
          />
        ) : null}
      </div>
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={remove}
        title={t("deposits.pages.removeTitle")}
        description={t("deposits.pages.removeDescription")}
        confirmLabel={t("common.delete")}
        isPending={actions.removePage.isPending}
      />
    </Card>
  );
}
