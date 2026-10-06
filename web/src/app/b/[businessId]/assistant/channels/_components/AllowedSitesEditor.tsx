"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconGlobe, IconPlus, IconTrash } from "@/components/icons";
import { Badge, Button, Field, Input, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { hasSite, isSameSiteList, MAX_ALLOWED_SITES, siteLabel, siteOrigin } from "../_lib/allowedSites";

type AllowedSitesView = Schema<"WidgetAllowedOriginsView">;
type AddError = "invalid" | "duplicate" | null;

/**
 * The list of allowed websites and, for an owner, the address field that
 * adds one, a remove button per site and Save. Addresses are read as the
 * API stores them (scheme, host and port), so a typo or a site already on
 * the list is caught before saving.
 */
export function AllowedSitesEditor({
  saved,
  canManage,
  onSaved,
}: {
  saved: readonly string[];
  canManage: boolean;
  onSaved: (view: AllowedSitesView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [sites, setSites] = useState<string[]>([...saved]);
  const [address, setAddress] = useState("");
  const [addError, setAddError] = useState<AddError>(null);
  const isChanged = !isSameSiteList(sites, saved);
  const isFull = sites.length >= MAX_ALLOWED_SITES;

  const save = useMutation((origins: string[]) =>
    api.PUT("/v1/businesses/{business_id}/channels/web/allowed-origins", {
      params: { path: { business_id: business.id } },
      body: { origins },
    }),
  );

  const add = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const origin = siteOrigin(address);
    if (origin === null) {
      setAddError("invalid");
      return;
    }
    if (hasSite(sites, origin)) {
      setAddError("duplicate");
      return;
    }
    setSites([...sites, origin]);
    setAddress("");
    setAddError(null);
  };

  const submit = async () => {
    const result = await save.run(sites);
    if (result.ok) {
      onSaved(result.data);
      toast.success(result.data.is_restricted ? t("widgetSites.savedToast") : t("widgetSites.clearedToast"));
    }
  };

  return (
    <div className="space-y-4">
      {sites.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-ink-muted">
          <IconGlobe className="size-4 shrink-0" aria-hidden />
          {t("widgetSites.empty")}
        </p>
      ) : (
        <ul aria-label={t("widgetSites.listLabel")} className="divide-y divide-line rounded-xl border border-line">
          {sites.map((site) => (
            <li key={site} className="flex min-w-0 items-center justify-between gap-3 px-3 py-2">
              <span dir="ltr" data-user-content className="min-w-0 truncate font-mono text-sm text-ink" title={site}>
                {siteLabel(site)}
              </span>
              {canManage ? (
                <Button
                  variant="danger-ghost"
                  size="sm"
                  aria-label={t("widgetSites.remove", { site: siteLabel(site) })}
                  leadingIcon={<IconTrash className="size-4" aria-hidden />}
                  onClick={() => setSites(sites.filter((other) => other !== site))}
                />
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {canManage ? (
        <form noValidate onSubmit={add} className="space-y-2">
          <Field
            label={t("widgetSites.addLabel")}
            hint={isFull ? t("widgetSites.full", { count: MAX_ALLOWED_SITES }) : t("widgetSites.addHint")}
            error={addError ? t(addError === "invalid" ? "widgetSites.invalid" : "widgetSites.duplicate") : undefined}
          >
            {(control) => (
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  {...control}
                  type="text"
                  inputMode="url"
                  dir="ltr"
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={300}
                  disabled={isFull}
                  placeholder={t("widgetSites.placeholder")}
                  value={address}
                  className="min-w-0 sm:flex-1"
                  onChange={(event) => {
                    setAddress(event.target.value);
                    setAddError(null);
                  }}
                />
                <Button
                  type="submit"
                  variant="secondary"
                  size="md"
                  disabled={isFull || address.trim() === ""}
                  leadingIcon={<IconPlus className="size-4" aria-hidden />}
                >
                  {t("widgetSites.add")}
                </Button>
              </div>
            )}
          </Field>
        </form>
      ) : null}

      <p className="text-sm text-ink-muted">{t("widgetSites.alwaysAllowed")}</p>

      {canManage ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm" isLoading={save.isPending} loadingText={t("widgetSites.saving")} disabled={!isChanged} onClick={submit}>
            {t("widgetSites.save")}
          </Button>
          {isChanged ? <Badge tone="warning">{t("widgetSites.unsaved")}</Badge> : null}
        </div>
      ) : (
        <p className="text-sm text-ink-muted">{t("widgetSites.ownerOnly")}</p>
      )}
    </div>
  );
}
