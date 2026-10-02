"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Badge, Button, Card, Checkbox, ErrorState, LoadingBlock, useToast } from "@/components/ui";
import { IconFile } from "@/components/icons";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { memberLabel } from "../../_lib/team";
import { DpaReader } from "./DpaReader";

/** The data processing agreement: its version, who accepted it and when, reading and accepting it. */
export function DpaCard() {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const [isAgreed, setAgreed] = useState(false);
  const [isReading, setReading] = useState(false);
  const [hasRead, setHasRead] = useState(false);
  const dpa = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const accept = useApiMutation(() => api.POST("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: business.id } } }));

  const onAccept = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = await accept.run();
    if (result.ok) {
      dpa.setData(result.data);
      setAgreed(false);
      toast.success(t("settings.dpa.acceptedToast"));
    }
  };

  const data = dpa.data;
  const acceptance = data?.latest_acceptance;
  const acceptedBy = acceptance
    ? (() => {
        const member = business.members.find((item) => item.user_id === acceptance.accepted_by);
        return member ? memberLabel(member) : t("settings.dpa.someone");
      })()
    : "";
  const hasText = Boolean(data?.document_url);
  const canAccept = data !== undefined && !data.is_current_version_accepted && isOwner && hasText;

  return (
    <Card title={t("settings.dpa.title")} description={t("settings.dpa.description")}>
      {dpa.error?.code === "access_denied" ? (
        <OwnerOnlyState className="py-4" />
      ) : dpa.error && !data ? (
        <ErrorState error={dpa.error} onRetry={dpa.reload} className="py-6" />
      ) : !data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-24" />
      ) : (
        <div className="space-y-5">
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-ink-subtle">{t("settings.dpa.version")}</dt>
              <dd className="mt-0.5 font-medium text-ink">{data.current_document_version}</dd>
            </div>
            <div>
              <dt className="text-ink-subtle">{t("settings.dpa.status")}</dt>
              <dd className="mt-1">
                <Badge tone={data.is_current_version_accepted ? "success" : "warning"}>
                  {data.is_current_version_accepted ? t("settings.dpa.accepted") : t("settings.dpa.notAccepted")}
                </Badge>
              </dd>
            </div>
          </dl>
          {acceptance ? (
            <p className="text-sm text-ink-muted">
              {data.is_current_version_accepted
                ? t("settings.dpa.acceptedOn", { date: format.dateTime(acceptance.accepted_at), name: acceptedBy })
                : t("settings.dpa.oldAccepted", { version: acceptance.document_version })}
            </p>
          ) : null}
          {hasText ? (
            <div>
              <Button
                variant="secondary"
                leadingIcon={<IconFile className="size-4" aria-hidden />}
                onClick={() => {
                  setReading(true);
                  setHasRead(true);
                }}
              >
                {t("settings.dpaReader.read")}
              </Button>
            </div>
          ) : (
            <Alert tone="warning" title={t("settings.dpaReader.noTextTitle")}>
              {t("settings.dpaReader.noText")}
            </Alert>
          )}
          {canAccept ? (
            <form onSubmit={onAccept} className="space-y-4 rounded-xl border border-line bg-surface-muted/50 p-4">
              <Checkbox
                id="dpa-agree"
                checked={isAgreed}
                disabled={!hasRead}
                onChange={(event) => setAgreed(event.target.checked)}
                label={t("settings.dpa.checkbox", { version: data.current_document_version })}
                description={hasRead ? undefined : t("settings.dpaReader.readFirst")}
              />
              <Button type="submit" disabled={!isAgreed} isLoading={accept.isPending}>
                {t("settings.dpa.accept")}
              </Button>
            </form>
          ) : null}
        </div>
      )}

      <DpaReader
        open={isReading && data !== undefined}
        version={data?.current_document_version ?? ""}
        canConfirm={canAccept}
        onClose={() => setReading(false)}
        onConfirm={() => {
          setAgreed(true);
          setReading(false);
        }}
      />
    </Card>
  );
}
