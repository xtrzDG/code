"use client";

import { IconSearch, IconShield, IconUsers } from "@/components/icons";
import { RefreshFailed } from "@/components/insights/common";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  InlineError,
  Input,
  LoadingRegion,
  SkeletonRows,
} from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { erasureConfirmation } from "../../_lib/customers";
import { useDataRequests } from "../../_lib/useDataRequests";
import { CustomerRow } from "./CustomerRow";

/** Customers' requests: find a customer, export their data or erase it. */
export function DataRequestsCard() {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const requests = useDataRequests();
  const { query, setQuery, search, contacts, exporting, erasing, erasureError, lastErasure, displayName } = requests;

  if (contacts.error?.code === "access_denied") {
    return (
      <Card title={t("settings.requests.title")}>
        <OwnerOnlyState className="py-4" />
      </Card>
    );
  }

  const items = contacts.items ?? [];
  const isEmpty = items.length === 0;

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
          <LoadingRegion label={t("common.loading")}>
            <SkeletonRows rows={3} avatar />
          </LoadingRegion>
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
          <div className="space-y-3" aria-busy={contacts.isPlaceholder || contacts.isFetching}>
            {contacts.error ? <RefreshFailed error={contacts.error} onRetry={contacts.reload} /> : null}
            <ul className="divide-y divide-line rounded-xl border border-line">
              {items.map((contact) => (
                <CustomerRow
                  key={contact.id}
                  contact={contact}
                  name={displayName(contact)}
                  isExporting={exporting === contact.id}
                  onExport={() => requests.onExport(contact)}
                  onErase={() => requests.startErasing(contact)}
                />
              ))}
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
        onClose={requests.stopErasing}
        onConfirm={requests.onErase}
        isPending={requests.isErasing}
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

