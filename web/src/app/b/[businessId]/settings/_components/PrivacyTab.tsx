"use client";

import { useEffect, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { unwrap } from "@/api/result";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconShield } from "@/components/icons";
import { Alert, Badge, Button, Card, Checkbox, EmptyState, ErrorState, Field, Input, LoadingBlock, Modal, useToast } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { downloadJson, isoDay } from "@/components/workspace/helpers";
import { IconDownload, IconFile, IconSearch, IconUsers } from "@/components/workspace/icons";
import { InlineError } from "@/components/workspace/InlineError";
import { MarkdownDocument } from "@/components/workspace/MarkdownDocument";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useCursorList } from "@/components/workspace/useCursorList";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import {
  CONTACTS_PAGE_SIZE,
  contactSearchParam,
  erasureConfirmation,
  markErased,
  memberLabel,
  type ContactPage,
  type ContactSummary,
  type ErasureResult,
} from "../_lib/settings";

const SEARCH_DELAY_MS = 300;

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

/** The agreement text in a dialog, in the interface language when it exists. */
function DpaReader({
  open,
  version,
  canConfirm,
  onClose,
  onConfirm,
}: {
  open: boolean;
  version: string;
  canConfirm: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const { t, locale } = useI18n();
  const document = useApiQuery(
    () => api.GET("/v1/legal/dpa/{version}", { params: { path: { version }, query: { language: locale } } }),
    [version, locale],
    { enabled: open && version !== "" },
  );
  const data = document.data;

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title={data?.title ?? t("settings.dpa.title")}
      footer={
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
          {canConfirm && data ? <Button onClick={onConfirm}>{t("settings.dpaReader.confirmRead")}</Button> : null}
        </div>
      }
    >
      {document.error && !data ? (
        <ErrorState error={document.error} onRetry={document.reload} className="py-6" />
      ) : !data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-48" />
      ) : (
        <div className="space-y-4">
          {data.language !== locale ? (
            <Alert tone="info">{t("settings.dpaReader.otherLanguage", { language: languageName(data.language, locale) })}</Alert>
          ) : null}
          <MarkdownDocument source={data.text} lang={data.language} hideTitle />
        </div>
      )}
    </Modal>
  );
}

function DataRequestsCard() {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<string | undefined>(undefined);
  const [exporting, setExporting] = useState<string | null>(null);
  const [erasing, setErasing] = useState<ContactSummary | null>(null);
  const [erasureError, setErasureError] = useState<ApiError | null>(null);
  const [lastErasure, setLastErasure] = useState<ErasureResult | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(contactSearchParam(query)), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const contacts = useCursorList<ContactSummary, ContactPage>(
    (cursor) =>
      api.GET("/v1/businesses/{business_id}/contacts", {
        params: {
          path: { business_id: business.id },
          query: { search, limit: String(CONTACTS_PAGE_SIZE), ...(cursor ? { cursor } : {}) },
        },
      }),
    (contact) => contact.id,
    [business.id, search],
  );
  const erase = useApiMutation(
    (contactId: string) =>
      api.DELETE("/v1/businesses/{business_id}/contacts/{contact_id}", {
        params: { path: { business_id: business.id, contact_id: contactId } },
      }),
    { errorToast: false },
  );

  const displayName = (contact: ContactSummary) => contact.name || contact.phone_number || t("settings.requests.unnamed");

  const onExport = async (contact: ContactSummary) => {
    setExporting(contact.id);
    try {
      const data = await unwrap(
        api.GET("/v1/businesses/{business_id}/contacts/{contact_id}/export", {
          params: { path: { business_id: business.id, contact_id: contact.id } },
        }),
      );
      downloadJson(data, `${contact.id}-${isoDay(new Date())}.json`);
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
    const result = await erase.run(erasing.id);
    if (!result.ok) {
      setErasureError(result.error);
      return;
    }
    const erasedId = erasing.id;
    const erasedAt = Date.now() * 1000;
    setErasing(null);
    setLastErasure(result.data);
    contacts.updateItems((items) => items.map((item) => (item.id === erasedId ? markErased(item, erasedAt) : item)));
    toast.success(t("settings.requests.deleted"));
  };

  if (contacts.error?.code === "access_denied") {
    return (
      <Card title={t("settings.requests.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  const isEmpty = contacts.items.length === 0;

  return (
    <Card title={t("settings.requests.title")} description={t("settings.requests.description")}>
      <div className="space-y-6">
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

        <Field label={t("settings.requests.search")} hint={t("settings.customers.searchHint")}>
          {(control) => (
            <div className="relative max-w-md">
              <IconSearch className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
              <Input
                {...control}
                type="search"
                value={query}
                dir="auto"
                maxLength={100}
                className="pl-9"
                placeholder={t("settings.requests.searchPlaceholder")}
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
          )}
        </Field>

        {contacts.error && isEmpty ? (
          <ErrorState error={contacts.error} onRetry={contacts.reload} className="py-6" />
        ) : contacts.isLoading && isEmpty ? (
          <LoadingBlock label={t("common.loading")} className="min-h-24" />
        ) : isEmpty && search === undefined ? (
          <EmptyState
            className="py-6"
            icon={<IconUsers className="size-6" />}
            title={t("settings.requests.empty")}
            description={t("settings.requests.emptyDescription")}
          />
        ) : isEmpty ? (
          <p className="text-sm text-ink-muted" role="status">
            {t("settings.requests.noMatches")}
          </p>
        ) : (
          <div className="space-y-3" aria-busy={contacts.isLoading}>
            <ul className="divide-y divide-line rounded-xl border border-line">
              {contacts.items.map((contact) => {
                const name = displayName(contact);
                const isErased = Boolean(contact.erased_at);
                const channels = (contact.channels ?? []).map((channel) => t(CHANNEL_NAMES[channel]));
                return (
                  <li key={contact.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                    <div className="min-w-0 flex-1 basis-56">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                        {isErased ? (
                          <span className="text-ink-muted">{t("settings.customers.erasedName")}</span>
                        ) : (
                          <span dir="auto" className="break-words">
                            {name}
                          </span>
                        )}
                        {isErased ? <Badge tone="neutral">{t("settings.customers.erased")}</Badge> : null}
                        {!isErased && contact.is_phone_verified ? <Badge tone="success">{t("settings.customers.verifiedPhone")}</Badge> : null}
                      </p>
                      <p className="mt-0.5 text-xs text-ink-muted">
                        {[
                          contact.name && contact.phone_number ? contact.phone_number : null,
                          channels.length > 0 ? new Intl.ListFormat(locale, { type: "unit" }).format(channels) : null,
                          contact.conversation_count > 0 ? tp("settings.requests.conversations", contact.conversation_count) : null,
                          contact.booking_count > 0 ? tp("settings.customers.bookings", contact.booking_count) : null,
                          contact.lead_count > 0 ? tp("settings.customers.leads", contact.lead_count) : null,
                          isErased && contact.erased_at
                            ? t("settings.customers.erasedOn", { date: format.dateTime(contact.erased_at) })
                            : t("settings.customers.lastActivity", { date: format.dateTime(contact.last_activity_at) }),
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      <p className="mt-0.5 font-mono text-[11px] break-all text-ink-subtle">{contact.id}</p>
                    </div>
                    {isOwner && !isErased ? (
                      <div className="flex flex-wrap gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          leadingIcon={<IconDownload className="size-4" aria-hidden />}
                          isLoading={exporting === contact.id}
                          aria-label={t("settings.requests.exportLabel", { name })}
                          onClick={() => onExport(contact)}
                        >
                          {t("settings.requests.export")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className={DANGER_GHOST}
                          aria-label={t("settings.requests.deleteLabel", { name })}
                          onClick={() => {
                            setErasureError(null);
                            setErasing(contact);
                          }}
                        >
                          {t("settings.requests.delete")}
                        </Button>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
            <InlineError error={contacts.moreError} />
            {contacts.hasMore ? (
              <Button variant="secondary" size="sm" isLoading={contacts.isLoadingMore} onClick={contacts.loadMore}>
                {t("settings.requests.showMore")}
              </Button>
            ) : null}
          </div>
        )}
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
