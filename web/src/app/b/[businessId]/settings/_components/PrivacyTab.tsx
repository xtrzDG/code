"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconShield } from "@/components/icons";
import { Alert, Badge, Button, Card, Checkbox, EmptyState, ErrorState, Field, Input, LoadingBlock, useToast } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { downloadJson, isoDay } from "@/components/workspace/helpers";
import { IconDownload, IconSearch, IconUsers } from "@/components/workspace/icons";
import { OwnerOnlyNote, OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useI18n } from "@/i18n/client";

import {
  contactsFromConversations,
  erasureConfirmation,
  filterCustomers,
  memberLabel,
  parseContactId,
  type CustomerContact,
} from "../_lib/settings";

const CUSTOMERS_PAGE = 20;

/** The data processing agreement and customers' requests to export or erase their data. */
export function PrivacyTab() {
  return (
    <div className="space-y-6">
      <DpaCard />
      <DataRequestsCard />
    </div>
  );
}

function DpaCard() {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const [isAgreed, setAgreed] = useState(false);
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
          {!data.is_current_version_accepted && isOwner ? (
            <form onSubmit={onAccept} className="space-y-4 rounded-xl border border-line bg-surface-muted/50 p-4">
              <Checkbox
                id="dpa-agree"
                checked={isAgreed}
                onChange={(event) => setAgreed(event.target.checked)}
                label={t("settings.dpa.checkbox", { version: data.current_document_version })}
              />
              <Button type="submit" disabled={!isAgreed} isLoading={accept.isPending}>
                {t("settings.dpa.accept")}
              </Button>
            </form>
          ) : null}
        </div>
      )}
    </Card>
  );
}

type ErasureResult = Schema<"ContactErasureResult">;

function DataRequestsCard() {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const [query, setQuery] = useState("");
  const [visible, setVisible] = useState(CUSTOMERS_PAGE);
  const [contactIdText, setContactIdText] = useState("");
  const [contactIdError, setContactIdError] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [erasing, setErasing] = useState<CustomerContact | null>(null);
  const [erasureError, setErasureError] = useState<ApiError | null>(null);
  const [lastErasure, setLastErasure] = useState<ErasureResult | null>(null);

  const conversations = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/conversations", {
        // The feed is paged: the latest 200 conversations name the recent customers.
        params: { path: { business_id: business.id }, query: { limit: "200" } },
      }),
    [business.id],
  );
  const erase = useApiMutation(
    (contactId: string) =>
      api.DELETE("/v1/businesses/{business_id}/contacts/{contact_id}", {
        params: { path: { business_id: business.id, contact_id: contactId } },
      }),
    { errorToast: false },
  );

  const customers = contactsFromConversations(conversations.data?.items ?? []);
  const matches = filterCustomers(customers, query);
  const shown = matches.slice(0, visible);
  const displayName = (customer: CustomerContact) => customer.name || customer.phoneNumber || t("settings.requests.unnamed");

  const onExport = async (customer: Pick<CustomerContact, "contactId" | "name" | "phoneNumber">) => {
    setExporting(customer.contactId);
    try {
      const data = await unwrap(
        api.GET("/v1/businesses/{business_id}/contacts/{contact_id}/export", {
          params: { path: { business_id: business.id, contact_id: customer.contactId } },
        }),
      );
      downloadJson(data, `${customer.contactId}-${isoDay(new Date())}.json`);
      toast.success(t("settings.requests.exported"));
    } catch (error) {
      toast.error(error);
    } finally {
      setExporting(null);
    }
  };

  const onErase = async () => {
    if (!erasing) {
      return;
    }
    const result = await erase.run(erasing.contactId);
    if (!result.ok) {
      setErasureError(result.error);
      return;
    }
    setErasing(null);
    setLastErasure(result.data);
    conversations.reload();
    toast.success(t("settings.requests.deleted"));
  };

  const askErase = (customer: CustomerContact) => {
    setErasureError(null);
    setErasing(customer);
  };

  const byIdCustomer = (): CustomerContact | null => {
    const contactId = parseContactId(contactIdText);
    if (!contactId) {
      setContactIdError(true);
      return null;
    }
    return (
      customers.find((customer) => customer.contactId === contactId) ?? {
        contactId,
        name: null,
        phoneNumber: null,
        lastMessageAt: 0,
        conversationCount: 0,
        channels: [],
      }
    );
  };

  return (
    <Card title={t("settings.requests.title")} description={t("settings.requests.description")}>
      <div className="space-y-6">
        {!isOwner ? <OwnerOnlyNote /> : null}

        {lastErasure ? (
          <Alert tone="success" title={t("settings.requests.deleted")}>
            {t("settings.requests.deletedSummary", {
              messages: format.number(lastErasure.deleted_messages),
              recordings: format.number(lastErasure.deleted_recordings),
              conversations: format.number(lastErasure.anonymized_conversations),
              bookings: format.number(lastErasure.anonymized_bookings),
              leads: format.number(lastErasure.anonymized_leads),
              handoffs: format.number(lastErasure.anonymized_handoffs),
            })}
          </Alert>
        ) : null}

        <Field label={t("settings.requests.search")}>
          {(control) => (
            <div className="relative max-w-md">
              <IconSearch className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
              <Input
                {...control}
                type="search"
                value={query}
                dir="auto"
                className="pl-9"
                placeholder={t("settings.requests.searchPlaceholder")}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setVisible(CUSTOMERS_PAGE);
                }}
              />
            </div>
          )}
        </Field>

        {conversations.error && !conversations.data ? (
          <ErrorState error={conversations.error} onRetry={conversations.reload} className="py-6" />
        ) : !conversations.data ? (
          <LoadingBlock label={t("common.loading")} className="min-h-24" />
        ) : customers.length === 0 ? (
          <EmptyState
            className="py-6"
            icon={<IconUsers className="size-6" />}
            title={t("settings.requests.empty")}
            description={t("settings.requests.emptyDescription")}
          />
        ) : matches.length === 0 ? (
          <p className="text-sm text-ink-muted">{t("settings.requests.noMatches")}</p>
        ) : (
          <div className="space-y-3">
            <ul className="divide-y divide-line rounded-xl border border-line">
              {shown.map((customer) => {
                const name = displayName(customer);
                return (
                  <li key={customer.contactId} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                    <div className="min-w-0 flex-1 basis-56">
                      <p className="text-sm font-medium text-ink" dir="auto">
                        {name}
                      </p>
                      <p className="mt-0.5 text-xs text-ink-muted">
                        {[
                          customer.name && customer.phoneNumber ? customer.phoneNumber : null,
                          new Intl.ListFormat(locale, { type: "unit" }).format(customer.channels.map((channel) => t(CHANNEL_NAMES[channel]))),
                          tp("settings.requests.conversations", customer.conversationCount),
                          t("settings.requests.lastActivity", { date: format.dateTime(customer.lastMessageAt) }),
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      <p className="mt-0.5 font-mono text-[11px] break-all text-ink-subtle">{customer.contactId}</p>
                    </div>
                    {isOwner ? (
                      <div className="flex flex-wrap gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          leadingIcon={<IconDownload className="size-4" aria-hidden />}
                          isLoading={exporting === customer.contactId}
                          aria-label={t("settings.requests.exportLabel", { name })}
                          onClick={() => onExport(customer)}
                        >
                          {t("settings.requests.export")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className={DANGER_GHOST}
                          aria-label={t("settings.requests.deleteLabel", { name })}
                          onClick={() => askErase(customer)}
                        >
                          {t("settings.requests.delete")}
                        </Button>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
            {matches.length > shown.length ? (
              <Button variant="secondary" size="sm" onClick={() => setVisible((count) => count + CUSTOMERS_PAGE)}>
                {t("settings.requests.showMore")}
              </Button>
            ) : null}
          </div>
        )}

        {isOwner ? (
          <section aria-labelledby="request-by-id" className="space-y-3 border-t border-line pt-5">
            <h3 id="request-by-id" className="text-sm font-semibold text-ink">
              {t("settings.requests.byId")}
            </h3>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <Field
                label={t("settings.requests.contactId")}
                hint={t("settings.requests.byIdHint")}
                error={contactIdError ? t("settings.requests.invalidId") : undefined}
                className="flex-1"
              >
                {(control) => (
                  <Input
                    {...control}
                    value={contactIdText}
                    dir="ltr"
                    autoComplete="off"
                    spellCheck={false}
                    placeholder="contact_…"
                    onChange={(event) => {
                      setContactIdText(event.target.value);
                      setContactIdError(false);
                    }}
                  />
                )}
              </Field>
              <div className="flex gap-2 sm:mt-7">
                <Button
                  variant="secondary"
                  leadingIcon={<IconDownload className="size-4" aria-hidden />}
                  isLoading={exporting !== null && exporting === parseContactId(contactIdText)}
                  onClick={() => {
                    const customer = byIdCustomer();
                    if (customer) {
                      void onExport(customer);
                    }
                  }}
                >
                  {t("settings.requests.export")}
                </Button>
                <Button
                  variant="danger"
                  onClick={() => {
                    const customer = byIdCustomer();
                    if (customer) {
                      askErase(customer);
                    }
                  }}
                >
                  {t("settings.requests.delete")}
                </Button>
              </div>
            </div>
          </section>
        ) : null}
      </div>

      <ConfirmDialog
        open={erasing !== null}
        onClose={() => setErasing(null)}
        onConfirm={onErase}
        isPending={erase.isPending}
        error={erasureError}
        title={erasing ? t("settings.requests.deleteTitle", { name: displayName(erasing) }) : ""}
        confirmLabel={t("settings.requests.deleteConfirm")}
        confirmationText={erasing ? erasureConfirmation(erasing) : undefined}
      >
        <p className="flex gap-2">
          <IconShield className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
          <span>{t("settings.requests.deleteDescription")}</span>
        </p>
      </ConfirmDialog>
    </Card>
  );
}
