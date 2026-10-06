"use client";

import Link from "next/link";
import { useState } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Card, Field, InlineError, Input, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  AUDIENCE_LABELS,
  AUDIENCES,
  campaignBody,
  campaignErrors,
  campaignForm,
  daysLabel,
  hasErrors,
  isSameCampaign,
  RULE_HINTS,
  RULE_KINDS,
  RULE_LABELS,
  suggestionKey,
  type CampaignForm,
  type CampaignSettingsView,
} from "../_lib/returnVisitsModel";
import type { ReturnVisitsState } from "../_lib/useReturnVisits";

/**
 * The owner's choices: send the message or not, which one and when (the
 * niche's usual rule a click away), who may get it (everyone the rule
 * finds or one saved segment) and the most a month, with what always
 * holds (STOP, the do-not-contact list, two weeks between messages).
 */
export function ReturnVisitsFormCard({ stored, state }: { stored: CampaignSettingsView; state: ReturnVisitsState }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [form, setForm] = useState<CampaignForm>(() => campaignForm(stored));
  const [isChecked, setIsChecked] = useState(false);
  const { save, settings, segments } = state;
  const errors = campaignErrors(form);
  const shown = isChecked ? errors : { delayDays: null, monthlyCap: null, segment: null };
  const update = (change: Partial<CampaignForm>) => setForm((current) => ({ ...current, ...change }));
  const segmentItems = segments.data?.items ?? [];
  const isSuggested = form.ruleKind === stored.niche_rule_kind && form.delayDays.trim() === String(stored.niche_delay_days);

  const submit = async () => {
    setIsChecked(true);
    if (hasErrors(campaignErrors(form))) {
      return;
    }
    const result = await save.run(campaignBody(form));
    if (result.ok) {
      settings.setData(result.data);
      setForm(campaignForm(result.data));
      setIsChecked(false);
      toast.success(t("returnVisits.settings.saved"));
    }
  };

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <Card title={t("returnVisits.settings.title")} description={t("returnVisits.settings.description")}>
        <div className="space-y-5">
          <div className="flex items-start justify-between gap-4">
            <p className="min-w-0 text-sm font-medium text-ink">{t("returnVisits.settings.toggle")}</p>
            <Switch
              checked={form.isEnabled}
              onChange={(isEnabled) => update({ isEnabled })}
              label={t("returnVisits.settings.toggle")}
              disabled={save.isPending}
            />
          </div>

          <div className="grid items-start gap-4 sm:grid-cols-[minmax(0,1fr)_14rem]">
            <Field label={t("returnVisits.settings.rule")} hint={t(RULE_HINTS[form.ruleKind])}>
              {(control) => (
                <Select
                  {...control}
                  value={form.ruleKind}
                  disabled={save.isPending}
                  onChange={(event) => update({ ruleKind: event.target.value as CampaignForm["ruleKind"] })}
                >
                  {RULE_KINDS.map((rule) => (
                    <option key={rule} value={rule}>
                      {t(RULE_LABELS[rule])}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label={t(daysLabel(form.ruleKind))} error={shown.delayDays ? t(shown.delayDays) : undefined}>
              {(control) => (
                <Input
                  {...control}
                  inputMode="numeric"
                  autoComplete="off"
                  value={form.delayDays}
                  disabled={save.isPending}
                  onChange={(event) => update({ delayDays: event.target.value })}
                />
              )}
            </Field>
          </div>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
            <span>
              {tp(suggestionKey(stored.niche_rule_kind), stored.niche_delay_days, {
                rule: t(RULE_LABELS[stored.niche_rule_kind]),
                count: stored.niche_delay_days,
              })}
            </span>
            {isSuggested ? null : (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={save.isPending}
                onClick={() => update({ ruleKind: stored.niche_rule_kind, delayDays: String(stored.niche_delay_days) })}
              >
                {t("returnVisits.settings.useSuggested")}
              </Button>
            )}
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("returnVisits.settings.audience")}>
              {(control) => (
                <Select
                  {...control}
                  value={form.audience}
                  disabled={save.isPending}
                  onChange={(event) => update({ audience: event.target.value as CampaignForm["audience"] })}
                >
                  {AUDIENCES.map((audience) => (
                    <option key={audience} value={audience}>
                      {t(AUDIENCE_LABELS[audience])}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            {form.audience === "segment" ? (
              <Field label={t("returnVisits.settings.segment")} error={shown.segment ? t(shown.segment) : undefined}>
                {(control) => (
                  <Select
                    {...control}
                    value={form.segmentId}
                    disabled={save.isPending || segmentItems.length === 0}
                    onChange={(event) => update({ segmentId: event.target.value })}
                  >
                    <option value="">{t("returnVisits.settings.chooseSegment")}</option>
                    {segmentItems.map((segment) => (
                      <option key={segment.id} value={segment.id}>
                        {segment.name}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ) : null}
          </div>
          {form.audience === "segment" && segments.data && segmentItems.length === 0 ? (
            <p className="text-sm text-ink-muted">
              {t("returnVisits.settings.noSegments")}{" "}
              <Link
                href={businessPath(business.id, "customers/segments")}
                className="font-medium text-accent underline underline-offset-2 hover:no-underline"
              >
                {t("returnVisits.settings.toSegments")}
              </Link>
            </p>
          ) : null}

          <Field
            label={t("returnVisits.settings.cap")}
            hint={t("returnVisits.settings.capHint")}
            error={shown.monthlyCap ? t(shown.monthlyCap) : undefined}
          >
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                autoComplete="off"
                className="max-w-40"
                value={form.monthlyCap}
                disabled={save.isPending}
                onChange={(event) => update({ monthlyCap: event.target.value })}
              />
            )}
          </Field>
          <p className="text-sm text-ink">
            {tp("returnVisits.settings.monthSent", stored.month_sent_count, { count: stored.month_sent_count, cap: stored.monthly_cap })}
          </p>
          <div className="space-y-2 rounded-xl bg-surface-muted px-3 py-2.5 text-sm text-ink-muted">
            <p>{t("returnVisits.settings.honours")}</p>
            <p>{t("returnVisits.settings.whatsapp")}</p>
          </div>

          <InlineError error={save.error} />
          <div className="flex justify-end">
            <Button type="submit" disabled={isSameCampaign(form, stored)} isLoading={save.isPending} loadingText={t("common.saving")}>
              {t("returnVisits.settings.save")}
            </Button>
          </div>
        </div>
      </Card>
    </form>
  );
}
