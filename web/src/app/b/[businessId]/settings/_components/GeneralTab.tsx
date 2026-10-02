"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { useCountryProfile } from "@/api/catalog";
import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { BusinessStatusBadge } from "@/components/business/BusinessStatusBadge";
import { useBusiness } from "@/components/business/BusinessContext";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  Checkbox,
  ErrorState,
  Field,
  Fieldset,
  Input,
  LoadingBlock,
  Select,
  useToast,
} from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { Facts } from "@/components/workspace/Facts";
import { IconPause, IconPlay } from "@/components/workspace/icons";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { countryFlag, countryName } from "@/lib/countries";
import { cn } from "@/lib/cn";
import { capitalizeFirst, languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import {
  MAX_BUSINESS_NAME_LENGTH,
  MAX_CITY_LENGTH,
  MAX_RETENTION_DAYS,
  MIN_RETENTION_DAYS,
  afterStatusSwitch,
  buildGeneralChanges,
  changesFromRevision,
  generalFormFrom,
  hasChanges,
  isStaleRevision,
  languageChoices,
  rebaseGeneralForm,
  toggleLanguage,
  type BusinessView,
  type GeneralError,
  type GeneralField,
  type GeneralForm,
  type SettingsChanges,
} from "../_lib/settings";

const GENERAL_ERRORS: Record<GeneralError, MessageKey> = {
  required: "settings.general.errors.required",
  tooLong: "settings.general.errors.tooLong",
  languages: "settings.general.errors.languages",
  retention: "settings.general.errors.retention",
};

const PLAN_NAMES: Record<BusinessView["plan_key"], MessageKey> = {
  chat: "workspace.plans.chat",
  voice_and_chat: "workspace.plans.voice_and_chat",
  plus: "workspace.plans.plus",
};

/** Every IANA zone the browser knows (for businesses outside the country's usual zones). */
function allTimeZones(): string[] {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return [];
  }
}

/**
 * Business details, languages and time, recording retention; and the
 * assistant's live/paused switch. The form starts from the business as
 * stored when the tab opens (the layout's copy may be older), and saves
 * carry the business revision they were made from. A save refused because
 * someone saved since is put on top of what is stored now: when nobody
 * else changed the same fields, it is saved again at once; otherwise those
 * fields show the stored values, the rest keeps what was typed, and the
 * form says so.
 */
export function GeneralTab() {
  const { t } = useI18n();
  const { business } = useBusiness();
  // The layout loads the business once and keeps it across pages, so a save
  // made since (platform bot, billing, another owner) leaves its revision
  // behind: start from the business as stored now, else the first save is
  // refused as stale.
  const stored = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  // The business as the status switch last saved it: the form takes over
  // its revision, so its next save is not refused for this tab's own change.
  const [switched, setSwitched] = useState<BusinessView | null>(null);
  return (
    <div className="space-y-6">
      <AssistantStatusCard onSaved={setSwitched} />
      {stored.data ? (
        <GeneralSettingsForm key={business.id} initial={stored.data} switched={switched} />
      ) : stored.error ? (
        <ErrorState error={stored.error} onRetry={stored.reload} className="py-6" />
      ) : (
        <LoadingBlock label={t("common.loading")} className="min-h-48" />
      )}
    </div>
  );
}

function GeneralSettingsForm({ initial, switched }: { initial: BusinessView; switched: BusinessView | null }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [loaded, setLoaded] = useState<BusinessView>(initial);
  const [form, setForm] = useState<GeneralForm>(() => generalFormFrom(initial));
  const [errors, setErrors] = useState<Partial<Record<GeneralField, GeneralError>>>({});
  const [isStale, setStale] = useState(false);
  // Refused as stale, but what is stored now could not be loaded either.
  const [isReloadFailed, setReloadFailed] = useState(false);
  // The status switch changes no field of this form, only the revision.
  const baseline = afterStatusSwitch(loaded, switched);

  const isClient = useIsClient();
  const profile = useCountryProfile(business.country_code);
  const catalog = useApiQuery(() => api.GET("/v1/catalog/languages", { params: { query: { language: locale } } }), [locale]);
  const save = useApiMutation(
    (changes: SettingsChanges) =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: changes }),
    { errorToast: false },
  );
  // Both a refused answer and a network failure come back as a result.
  const reload = useApiMutation(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    { errorToast: false },
  );

  const catalogNames = useMemo(() => {
    const names = new Map<string, string>();
    for (const item of catalog.data?.languages ?? []) {
      names.set(item.profile.tag, capitalizeFirst(item.display_name, locale));
    }
    return names;
  }, [catalog.data, locale]);
  const labelOf = (tag: string) => catalogNames.get(tag) ?? languageName(tag, locale);

  const countryProfile = profile.data && profile.data.profile.country_code === business.country_code ? profile.data : undefined;
  const choices = languageChoices(
    baseline.languages,
    countryProfile?.default_customer_languages.map((option) => option.tag) ?? [],
    countryProfile?.on_request_customer_languages.map((option) => option.tag) ?? [],
    form.languages,
  );
  const addable = (catalog.data?.languages ?? [])
    .filter((item) => !choices.includes(item.profile.tag))
    .sort((left, right) => left.display_name.localeCompare(right.display_name, locale));
  const ownerLanguages = languageChoices(["ka", "ru", "en"], [baseline.owner_language], form.languages);

  const countryZones = countryProfile?.timezones ?? [];
  const browserZones = useMemo(() => (isClient ? allTimeZones() : []), [isClient]);
  const otherZones = browserZones.filter((zone) => !countryZones.some((option) => option.name === zone));

  const result = buildGeneralChanges(baseline, form);
  const isDirty = !result.ok || hasChanges(result.changes);
  const disabled = !isOwner || save.isPending || reload.isPending;

  const update = <Field extends GeneralField>(field: Field, value: GeneralForm[Field]) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const saved = (stored: BusinessView) => {
    setLoaded(stored);
    setForm(generalFormFrom(stored));
    router.refresh();
    toast.success(t("settings.general.saved"));
  };

  /**
   * Save `typed` (made from `base`). Refused because someone saved since:
   * put it on top of what is stored now, and save once more when nobody
   * else changed the same fields.
   */
  const store = async (base: BusinessView, typed: GeneralForm, mayRetry: boolean): Promise<void> => {
    const built = buildGeneralChanges(base, typed);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    if (!hasChanges(built.changes)) {
      // What was typed is what is stored now.
      saved(base);
      return;
    }
    const answer = await save.run(changesFromRevision(built.changes, base));
    if (answer.ok) {
      saved(answer.data);
      return;
    }
    if (!isStaleRevision(answer.error)) {
      toast.error(answer.error);
      return;
    }
    const latest = await reload.run();
    router.refresh();
    if (!latest.ok) {
      // Do not claim the form shows what is stored: it still shows the
      // owner's own (refused) changes.
      setReloadFailed(true);
      toast.show({ tone: "error", title: t("settings.general.staleTitle") });
      return;
    }
    const rebased = rebaseGeneralForm(base, latest.data, typed);
    setLoaded(latest.data);
    setForm(rebased.form);
    setErrors({});
    if (rebased.conflicts.length === 0 && mayRetry) {
      await store(latest.data, rebased.form, false);
      return;
    }
    setStale(true);
    toast.show({ tone: "error", title: t("settings.general.staleTitle") });
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    if (!hasChanges(result.changes)) {
      toast.info(t("settings.general.noChanges"));
      return;
    }
    setStale(false);
    setReloadFailed(false);
    await store(baseline, form, true);
  };

  const loadCurrent = async () => {
    const latest = await reload.run();
    if (!latest.ok) {
      toast.error(latest.error);
      return;
    }
    const rebased = rebaseGeneralForm(baseline, latest.data, form);
    setLoaded(latest.data);
    setForm(rebased.form);
    setErrors({});
    setReloadFailed(false);
    setStale(true);
    router.refresh();
  };

  const errorText = (field: GeneralField) => (errors[field] ? t(GENERAL_ERRORS[errors[field]]) : undefined);

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      {isReloadFailed ? (
        <Alert
          tone="danger"
          title={t("settings.general.staleTitle")}
          action={
            <Button variant="secondary" size="sm" isLoading={reload.isPending} onClick={() => void loadCurrent()}>
              {t("settings.general.staleReload")}
            </Button>
          }
        >
          {t("settings.general.staleReloadFailed")}
        </Alert>
      ) : null}
      {isStale ? (
        <Alert
          tone="warning"
          title={t("settings.general.staleTitle")}
          action={
            <Button variant="secondary" size="sm" onClick={() => setStale(false)}>
              {t("common.close")}
            </Button>
          }
        >
          {t("settings.general.staleDescription")}
        </Alert>
      ) : null}
      <Card title={t("settings.general.businessTitle")}>
        <div className="space-y-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <Field label={t("settings.general.name")} required error={errorText("name")}>
              {(control) => (
                <Input
                  {...control}
                  value={form.name}
                  maxLength={MAX_BUSINESS_NAME_LENGTH}
                  dir="auto"
                  autoComplete="organization"
                  disabled={disabled}
                  onChange={(event) => update("name", event.target.value)}
                />
              )}
            </Field>
            <Field label={t("settings.general.city")} optionalLabel={t("common.optional")} error={errorText("city")}>
              {(control) => (
                <Input
                  {...control}
                  value={form.city}
                  maxLength={MAX_CITY_LENGTH}
                  dir="auto"
                  autoComplete="address-level2"
                  disabled={disabled}
                  onChange={(event) => update("city", event.target.value)}
                />
              )}
            </Field>
          </div>
          <Facts
            columns={4}
            items={[
              {
                label: t("settings.general.country"),
                value: `${countryFlag(baseline.country_code)} ${countryName(baseline.country_code, locale)}`,
              },
              { label: t("settings.general.currency"), value: baseline.currency_code },
              {
                label: t("settings.general.dataRegion"),
                value: t(baseline.data_region === "us" ? "settings.general.dataRegions.us" : "settings.general.dataRegions.eu"),
              },
              {
                label: t("settings.general.plan"),
                value: (
                  <Link href={businessPath(baseline.id, "billing")} className="text-accent hover:underline" title={t("settings.general.planHint")}>
                    {t(PLAN_NAMES[baseline.plan_key])}
                  </Link>
                ),
              },
            ]}
          />
        </div>
      </Card>

      <Card title={t("settings.general.languagesTitle")}>
        <div className="space-y-6">
          <Field label={t("settings.general.timezone")} hint={t("settings.general.timezoneHint")}>
            {(control) => (
              <Select {...control} value={form.timezone} disabled={disabled} onChange={(event) => update("timezone", event.target.value)}>
                {countryZones.length > 0 ? (
                  <optgroup label={t("settings.general.countryTimezones")}>
                    {countryZones.map((zone) => (
                      <option key={zone.name} value={zone.name}>
                        {zone.display_name}
                      </option>
                    ))}
                  </optgroup>
                ) : null}
                {!countryZones.some((zone) => zone.name === form.timezone) && !otherZones.includes(form.timezone) ? (
                  <option value={form.timezone}>{form.timezone}</option>
                ) : null}
                {otherZones.length > 0 ? (
                  <optgroup label={t("settings.general.allTimezones")}>
                    {otherZones.map((zone) => (
                      <option key={zone} value={zone}>
                        {zone}
                      </option>
                    ))}
                  </optgroup>
                ) : null}
              </Select>
            )}
          </Field>

          <Fieldset legend={t("settings.general.languages")} hint={t("settings.general.languagesHint")} error={errorText("languages")}>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {choices.map((tag) => (
                <Checkbox
                  key={tag}
                  id={`settings-language-${tag}`}
                  checked={form.languages.includes(tag)}
                  disabled={disabled}
                  onChange={(event) => update("languages", toggleLanguage(form.languages, tag, event.target.checked, choices))}
                  label={labelOf(tag)}
                />
              ))}
            </div>
            {addable.length > 0 && isOwner ? (
              <Field label={t("settings.general.addLanguage")} className="max-w-sm">
                {(control) => (
                  <Select
                    {...control}
                    value=""
                    disabled={disabled}
                    onChange={(event) => {
                      const tag = event.target.value;
                      if (tag) {
                        update("languages", toggleLanguage(form.languages, tag, true, choices));
                      }
                    }}
                  >
                    <option value="">{t("settings.general.addLanguagePlaceholder")}</option>
                    {addable.map((item) => (
                      <option key={item.profile.tag} value={item.profile.tag}>
                        {capitalizeFirst(item.display_name, locale)}
                        {item.profile.native_name && item.profile.native_name !== item.display_name ? ` — ${item.profile.native_name}` : ""}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ) : null}
          </Fieldset>

          <div className="grid gap-6 sm:grid-cols-2">
            <Field label={t("settings.general.defaultLanguage")} hint={t("settings.general.defaultLanguageHint")}>
              {(control) => (
                <Select
                  {...control}
                  value={form.languages.includes(form.defaultLanguage) ? form.defaultLanguage : (form.languages[0] ?? "")}
                  disabled={disabled || form.languages.length === 0}
                  onChange={(event) => update("defaultLanguage", event.target.value)}
                >
                  {form.languages.map((tag) => (
                    <option key={tag} value={tag}>
                      {labelOf(tag)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label={t("settings.general.ownerLanguage")}>
              {(control) => (
                <Select {...control} value={form.ownerLanguage} disabled={disabled} onChange={(event) => update("ownerLanguage", event.target.value)}>
                  {ownerLanguages.map((tag) => (
                    <option key={tag} value={tag}>
                      {labelOf(tag)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
        </div>
      </Card>

      <Card title={t("settings.general.recordingsTitle")}>
        <Field label={t("settings.general.retention")} hint={t("settings.general.retentionHint")} error={errorText("retentionDays")}>
          {(control) => (
            <div className="flex items-center gap-3">
              <div className="w-32">
                <Input
                  {...control}
                  type="number"
                  inputMode="numeric"
                  min={MIN_RETENTION_DAYS}
                  max={MAX_RETENTION_DAYS}
                  step={1}
                  value={form.retentionDays}
                  disabled={disabled}
                  onChange={(event) => update("retentionDays", event.target.value)}
                />
              </div>
              <span className="text-sm text-ink-muted">{t("settings.general.retentionUnit")}</span>
            </div>
          )}
        </Field>
      </Card>

      {isOwner ? (
        <div
          className={cn(
            "flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end",
            isDirty &&
              "sticky bottom-0 z-10 -mx-4 border-t border-line bg-canvas/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border sm:px-4",
          )}
        >
          {isDirty ? <p className="text-sm text-ink-muted sm:mr-auto">{t("settings.general.unsaved")}</p> : null}
          <Button
            variant="secondary"
            disabled={!isDirty || save.isPending}
            onClick={() => {
              setForm(generalFormFrom(baseline));
              setErrors({});
            }}
          >
            {t("settings.general.discard")}
          </Button>
          <Button type="submit" isLoading={save.isPending} loadingText={t("common.saving")} disabled={!isDirty}>
            {t("settings.general.save")}
          </Button>
        </div>
      ) : null}
    </form>
  );
}

function AssistantStatusCard({ onSaved }: { onSaved: (business: BusinessView) => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [isConfirmingPause, setConfirmingPause] = useState(false);
  const [pauseError, setPauseError] = useState<ApiError | null>(null);
  const [status, setStatus] = useState(business.status);
  const switchStatus = useApiMutation(
    (next: "live" | "paused") =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: { status: next } }),
    { errorToast: false },
  );

  const run = async (next: "live" | "paused") => {
    // Only the status is sent: pausing or resuming overwrites no other setting.
    const result = await switchStatus.run(next);
    if (result.ok) {
      setStatus(result.data.status);
      onSaved(result.data);
      setConfirmingPause(false);
      router.refresh();
      toast.success(t(next === "paused" ? "settings.status.pausedToast" : "settings.status.resumedToast"));
    } else if (next === "paused") {
      setPauseError(result.error);
    } else {
      toast.error(result.error);
    }
  };

  const description =
    status === "live" ? t("settings.status.live") : status === "paused" ? t("settings.status.paused") : t("settings.status.notLive");

  return (
    <Card
      title={t("settings.status.title")}
      actions={<BusinessStatusBadge status={status} />}
      footer={
        isOwner && (status === "live" || status === "paused") ? (
          status === "live" ? (
            <Button
              variant="secondary"
              leadingIcon={<IconPause className="size-4" aria-hidden />}
              onClick={() => {
                setPauseError(null);
                setConfirmingPause(true);
              }}
            >
              {t("settings.status.pause")}
            </Button>
          ) : (
            <Button leadingIcon={<IconPlay className="size-4" aria-hidden />} isLoading={switchStatus.isPending} onClick={() => run("live")}>
              {t("settings.status.resume")}
            </Button>
          )
        ) : status === "onboarding" || status === "testing" ? (
          <ButtonLink href={businessPath(business.id, "assistant")} variant="secondary">
            {t("settings.status.openAssistant")}
          </ButtonLink>
        ) : undefined
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-ink-muted">{description}</p>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink-subtle">{t("settings.status.serviceMode")}:</span>
          <Badge tone={business.service_mode === "full" ? "success" : "danger"}>
            {t(business.service_mode === "full" ? "billing.serviceModes.full" : "billing.serviceModes.leads_only")}
          </Badge>
        </div>
        {business.service_mode === "leads_only" ? (
          <Alert tone="warning">
            <p>{t("settings.status.leadsOnlyHint")}</p>
            <ButtonLink href={businessPath(business.id, "billing")} size="sm" variant="secondary" className="mt-3">
              {t("channels.openBilling")}
            </ButtonLink>
          </Alert>
        ) : null}
      </div>
      <ConfirmDialog
        open={isConfirmingPause}
        onClose={() => setConfirmingPause(false)}
        onConfirm={() => run("paused")}
        isPending={switchStatus.isPending}
        error={pauseError}
        title={t("settings.status.pauseTitle")}
        description={t("settings.status.pauseDescription")}
        confirmLabel={t("settings.status.pause")}
      />
    </Card>
  );
}
