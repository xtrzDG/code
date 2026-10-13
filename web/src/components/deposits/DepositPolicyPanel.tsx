"use client";

import Link from "next/link";
import { useId, useState, type FormEvent } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, ErrorState, Field, Input, LoadingRegion, Select, SkeletonText, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  pagesForRule,
  POLICY_RULES,
  RULE_LABELS,
  policyForm,
  policyFormErrors,
  policyOf,
  policyRequestBody,
  type DepositSettingsView,
  type PolicyForm,
  type PolicyRuleChoice,
  type PolicyTarget,
} from "./depositModel";
import { useDepositSettings, useDepositSettingsActions } from "./useDeposits";

/**
 * The deposit of one table, room or master, one service, or the banquet
 * requests: no deposit, a fixed sum, a sum per guest or a percent of the
 * booking's value, from a number of guests on. It saves on its own
 * (owners); the amount the assistant asks always comes from here.
 */
export function DepositPolicyPanel({
  target,
  heading,
  linksSettings = true,
}: {
  target: PolicyTarget;
  heading?: string;
  /** False on Settings → Deposits itself. */
  linksSettings?: boolean;
}) {
  const { t } = useI18n();
  const settings = useDepositSettings();

  if (!settings.data) {
    return settings.error ? (
      <ErrorState error={settings.error} onRetry={settings.reload} className="py-4" />
    ) : (
      <LoadingRegion label={t("common.loading")}>
        <SkeletonText lines={2} />
      </LoadingRegion>
    );
  }
  return (
    <PolicyEditor
      key={JSON.stringify(policyOf(settings.data, target))}
      settings={settings.data}
      target={target}
      heading={heading}
      linksSettings={linksSettings}
      onSaved={settings.setData}
    />
  );
}

function PolicyEditor({
  settings,
  target,
  heading,
  linksSettings,
  onSaved,
}: {
  settings: DepositSettingsView;
  target: PolicyTarget;
  heading?: string;
  linksSettings: boolean;
  onSaved: (settings: DepositSettingsView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const formId = useId();
  const actions = useDepositSettingsActions();
  const stored = policyOf(settings, target);
  const [form, setForm] = useState<PolicyForm>(() => policyForm(stored));
  const [showErrors, setShowErrors] = useState(false);
  const currency = settings.currency_code;
  const errors = showErrors ? policyFormErrors(form, currency) : {};
  const links = settings.payment_links ?? [];
  const hasPage = links.length > 0;
  const pages = pagesForRule(links, form.rule);

  const change = (patch: Partial<PolicyForm>) => setForm((current) => ({ ...current, ...patch }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setShowErrors(true);
    if (Object.keys(policyFormErrors(form, currency)).length > 0) {
      return;
    }
    const result = await actions.setPolicy.run(policyRequestBody(form, target, currency, links));
    if (result.ok) {
      onSaved(result.data);
      toast.success(t(form.rule === "none" ? "deposits.policy.removed" : "deposits.policy.saved"));
    }
  };

  const settingsLink = (
    <Link href={businessPath(business.id, "settings/deposits")} className="font-medium text-accent underline underline-offset-2 hover:no-underline">
      {t("deposits.policy.openSettings")}
    </Link>
  );
  const isAmount = form.rule === "fixed" || form.rule === "per_guest";

  return (
    <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-ink">{heading ?? t("deposits.policy.title")}</h3>
        <p className="text-sm text-ink-muted">{t("deposits.policy.description")}</p>
      </div>
      {!settings.is_enabled || !hasPage ? (
        <Alert tone="info">
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>{t(!hasPage ? "deposits.policy.noPage" : "deposits.policy.off")}</span>
            {linksSettings ? settingsLink : null}
          </p>
        </Alert>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label={t("deposits.policy.rule")} className="sm:col-span-3">
          {(control) => (
            <Select {...control} value={form.rule} onChange={(event) => change({ rule: event.target.value as PolicyRuleChoice })}>
              {POLICY_RULES.map((rule) => (
                <option key={rule} value={rule}>
                  {t(RULE_LABELS[rule])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {isAmount ? (
          <Field
            label={t(form.rule === "per_guest" ? "deposits.policy.amountPerGuest" : "deposits.policy.amount", { currency })}
            error={errors.amount && t(errors.amount)}
            className="sm:col-span-2"
          >
            {(control) => (
              <Input
                {...control}
                inputMode="decimal"
                autoComplete="off"
                value={form.amount}
                onChange={(event) => change({ amount: event.target.value })}
              />
            )}
          </Field>
        ) : null}
        {form.rule === "percent_of_value" ? (
          <Field label={t("deposits.policy.percent")} error={errors.percent && t(errors.percent)} className="sm:col-span-2">
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                autoComplete="off"
                value={form.percent}
                onChange={(event) => change({ percent: event.target.value })}
              />
            )}
          </Field>
        ) : null}
        {form.rule !== "none" ? (
          <Field
            label={t("deposits.policy.minParty")}
            optionalLabel={t("common.optional")}
            hint={t("deposits.policy.minPartyHint")}
            error={errors.minPartySize && t(errors.minPartySize)}
          >
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                autoComplete="off"
                value={form.minPartySize}
                onChange={(event) => change({ minPartySize: event.target.value })}
              />
            )}
          </Field>
        ) : null}
        {form.rule !== "none" && pages.some((page) => page.id !== settings.default_payment_link_id) ? (
          <Field label={t("deposits.policy.page")} hint={t("deposits.policy.pageHint")} className="sm:col-span-3">
            {(control) => (
              <Select
                {...control}
                value={pages.some((page) => page.id === form.paymentLinkId) ? form.paymentLinkId : ""}
                onChange={(event) => change({ paymentLinkId: event.target.value })}
              >
                <option value="">{t("deposits.policy.defaultPage")}</option>
                {pages.map((page) => (
                  <option key={page.id} value={page.id}>
                    {page.label} · {page.host}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        ) : null}
      </div>
      <div className="flex justify-end">
        <Button type="submit" size="sm" variant="secondary" isLoading={actions.setPolicy.isPending} loadingText={t("common.saving")}>
          {t("deposits.policy.save")}
        </Button>
      </div>
    </form>
  );
}
