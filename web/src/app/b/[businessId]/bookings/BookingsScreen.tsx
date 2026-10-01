"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCalendar, IconPlus } from "@/components/icons";
import { CustomerName, RefreshButton, RefreshFailed } from "@/components/insights/common";
import { ConfirmDialog } from "@/components/insights/ConfirmDialog";
import { CustomerMessageModal } from "@/components/insights/CustomerMessageModal";
import { todayIn } from "@/components/insights/dates";
import type { BookingPage, BookingStatus, BookingView } from "@/components/insights/types";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { usePagedQuery } from "@/components/insights/usePagedQuery";
import { Button, Card, EmptyState, ErrorState, LoadingBlock, Modal, PageHeader, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BookingEditForm } from "./_components/BookingEditForm";
import { BookingFiltersBar } from "./_components/BookingFiltersBar";
import { BookingForm } from "./_components/BookingForm";
import { BookingDays, BookingDetails, useBookingWhen } from "./_components/BookingList";
import {
  bookingActions,
  bookingApiQuery,
  bookingFiltersQuery,
  customerLanguage,
  isRangeValid,
  nightsOf,
  rangeDates,
  type BookingFilters,
} from "./_components/bookingModel";
import { CustomerLanguageSelect } from "./_components/CustomerLanguageSelect";
import { RescheduleForm } from "./_components/RescheduleForm";

type Dialog =
  | { kind: "none" }
  | { kind: "create" }
  | { kind: "details" | "edit" | "reschedule" | "cancel" | "noShow"; booking: BookingView }
  | { kind: "message"; title: string; text: string };

/**
 * Bookings in the business time zone (concept /bookings): filters by dates,
 * status and place (applied and paged by the API), a booking added by hand
 * with free slots, status changes, edits (party, place, notes, name),
 * moving and cancelling with the text for the customer.
 */
export function BookingsScreen({ initialFilters }: { initialFilters: BookingFilters }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const when = useBookingWhen();
  const businessId = business.id;
  const [today] = useState(() => todayIn(business.timezone));
  const [filters, setFiltersState] = useState(initialFilters);
  const [dialog, setDialog] = useState<Dialog>({ kind: "none" });
  const [cancelLanguage, setCancelLanguage] = useState(business.default_language);

  const range = rangeDates(filters, today);
  const rangeValid = isRangeValid(range);

  const bookings = usePagedQuery<BookingView, BookingPage>(
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/bookings", {
        params: {
          path: { business_id: businessId },
          query: { ...bookingApiQuery(filters, range), limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    [businessId, range.from, range.to, filters.status, filters.resourceId, filters.includeTest, filters.range],
    { enabled: rangeValid },
  );
  const resources = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } } }),
    [businessId],
  );

  const changeStatus = useApiMutation(
    (booking: BookingView, status: BookingStatus) =>
      api.PATCH("/v1/businesses/{business_id}/bookings/{booking_id}", {
        params: { path: { business_id: businessId, booking_id: booking.id } },
        body: { status },
      }),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );
  const cancel = useApiMutation(
    (booking: BookingView, language: string) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/cancel", {
        params: { path: { business_id: businessId, booking_id: booking.id }, query: { language } },
      }),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );

  const setFilters = (next: BookingFilters) => {
    setFiltersState(next);
    replaceUrlQuery(bookingFiltersQuery(next));
  };

  const replaceBooking = (updated: BookingView) =>
    bookings.updateItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));

  const resourceUnits = new Map((resources.data?.items ?? []).map((resource) => [resource.id, resource.booking_unit]));
  const isStay = (booking: BookingView) =>
    resourceUnits.get(booking.resource_id) === "night" || (booking.time === null && nightsOf(booking) > 0);

  const runStatus = async (booking: BookingView, status: BookingStatus) => {
    const result = await changeStatus.run(booking, status);
    if (result.ok) {
      replaceBooking(result.data);
      toast.success(t("bookings.updated"));
      setDialog({ kind: "details", booking: result.data });
    }
  };

  const runCancel = async (booking: BookingView) => {
    const result = await cancel.run(booking, cancelLanguage);
    if (result.ok) {
      replaceBooking(result.data.booking);
      toast.success(t("bookings.cancelled"));
      setDialog({ kind: "message", title: t("bookings.cancelled"), text: result.data.confirmation_text });
    }
  };

  const items = bookings.items ?? [];
  const openCancel = (booking: BookingView) => {
    setCancelLanguage(customerLanguage(booking, business));
    setDialog({ kind: "cancel", booking });
  };
  const close = () => setDialog({ kind: "none" });
  // Modal also reports a close when another dialog replaces it: only close the current one.
  const closeIf = (kind: Dialog["kind"]) => () =>
    setDialog((current) => (current.kind === kind ? { kind: "none" } : current));
  const dialogBooking = "booking" in dialog ? dialog.booking : null;
  const defaultDate = range.from && range.from > today ? range.from : today;

  return (
    <>
      <PageHeader
        title={t("nav.bookings")}
        description={t("pages.bookings.description")}
        actions={
          <>
            <RefreshButton onClick={bookings.reload} isRefreshing={bookings.isLoading && bookings.items !== undefined} />
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setDialog({ kind: "create" })}>
              {t("bookings.newBooking")}
            </Button>
          </>
        }
      />

      <div className="space-y-5">
        <BookingFiltersBar
          filters={filters}
          resources={resources.data?.items ?? []}
          rangeError={rangeValid ? null : t("bookings.rangeInvalid")}
          onChange={setFilters}
        />
        <p className="text-xs text-ink-subtle">{t("bookings.timeZoneNote", { timezone: business.timezone })}</p>
        {bookings.error && bookings.items ? <RefreshFailed error={bookings.error} onRetry={bookings.reload} /> : null}

        {!rangeValid ? null : bookings.items === undefined ? (
          <Card>
            {bookings.error ? (
              <ErrorState error={bookings.error} onRetry={bookings.reload} />
            ) : (
              <LoadingBlock label={t("bookings.loading")} />
            )}
          </Card>
        ) : items.length === 0 && !bookings.isLoading ? (
          <Card>
            <EmptyState
              icon={<IconCalendar className="size-6" />}
              title={t("bookings.emptyTitle")}
              description={t("bookings.emptyDescription")}
              action={
                <Button variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setDialog({ kind: "create" })}>
                  {t("bookings.newBooking")}
                </Button>
              }
            />
          </Card>
        ) : (
          <div className={bookings.isLoading ? "opacity-60 transition-opacity" : undefined} aria-busy={bookings.isLoading || undefined}>
            <BookingDays
              bookings={items}
              newestFirst={filters.range === "past"}
              isStay={isStay}
              onOpen={(booking) => setDialog({ kind: "details", booking })}
              paging={{
                hasMore: bookings.hasMore,
                isLoading: bookings.isLoadingMore,
                error: bookings.moreError,
                onMore: bookings.loadMore,
              }}
            />
          </div>
        )}
      </div>

      <Modal
        open={dialog.kind === "create"}
        onClose={closeIf("create")}
        title={t("bookings.form.title")}
        description={t("bookings.form.description")}
        size="lg"
      >
        <BookingForm
          resources={resources.data?.items ?? []}
          defaultDate={defaultDate}
          onCancel={close}
          onCreated={(result) => {
            bookings.reload();
            toast.success(t("bookings.created"));
            setDialog({ kind: "message", title: t("bookings.created"), text: result.confirmation_text });
          }}
        />
      </Modal>

      <Modal
        open={dialog.kind === "details"}
        onClose={closeIf("details")}
        title={dialogBooking ? <CustomerName name={dialogBooking.contact_name} /> : t("bookings.details.title")}
        size="md"
        footer={dialogBooking ? detailActions(dialogBooking) : undefined}
      >
        {dialogBooking ? <BookingDetails booking={dialogBooking} isStay={isStay(dialogBooking)} /> : null}
      </Modal>

      <Modal
        open={dialog.kind === "edit"}
        onClose={closeIf("edit")}
        title={t("bookings.edit.title")}
        description={
          dialogBooking
            ? t("bookings.reschedule.description", {
                name: dialogBooking.contact_name ?? t("insights.unknownCustomer"),
                when: when.full(dialogBooking, isStay(dialogBooking)),
              })
            : undefined
        }
      >
        {dialog.kind === "edit" ? (
          <BookingEditForm
            booking={dialog.booking}
            resources={resources.data?.items ?? []}
            onCancel={() => setDialog({ kind: "details", booking: dialog.booking })}
            onSaved={(updated) => {
              if (updated) {
                replaceBooking(updated);
                toast.success(t("bookings.updated"));
              }
              setDialog({ kind: "details", booking: updated ?? dialog.booking });
            }}
          />
        ) : null}
      </Modal>

      <Modal
        open={dialog.kind === "reschedule"}
        onClose={closeIf("reschedule")}
        title={t("bookings.reschedule.title")}
        description={
          dialogBooking
            ? t("bookings.reschedule.description", {
                name: dialogBooking.contact_name ?? t("insights.unknownCustomer"),
                when: when.full(dialogBooking, isStay(dialogBooking)),
              })
            : undefined
        }
      >
        {dialog.kind === "reschedule" ? (
          <RescheduleForm
            booking={dialog.booking}
            isStay={isStay(dialog.booking)}
            onCancel={() => setDialog({ kind: "details", booking: dialog.booking })}
            onDone={(result) => {
              replaceBooking(result.booking);
              bookings.reload();
              toast.success(t("bookings.rescheduled"));
              setDialog({ kind: "message", title: t("bookings.rescheduled"), text: result.confirmation_text });
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog.kind === "cancel"}
        title={t("bookings.confirmCancel.title")}
        description={
          dialogBooking
            ? t("bookings.confirmCancel.description", {
                name: dialogBooking.contact_name ?? t("insights.unknownCustomer"),
                when: when.full(dialogBooking, isStay(dialogBooking)),
              })
            : undefined
        }
        confirmLabel={t("bookings.confirmCancel.confirm")}
        cancelLabel={t("bookings.confirmCancel.keep")}
        isPending={cancel.isPending}
        onConfirm={() => (dialogBooking ? void runCancel(dialogBooking) : undefined)}
        onClose={() =>
          setDialog((current) => (current.kind === "cancel" ? { kind: "details", booking: current.booking } : current))
        }
      >
        <div className="mt-4">
          <CustomerLanguageSelect value={cancelLanguage} onChange={setCancelLanguage} />
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog.kind === "noShow"}
        title={t("bookings.confirmNoShow.title")}
        description={
          dialogBooking
            ? t("bookings.confirmNoShow.description", {
                name: dialogBooking.contact_name ?? t("insights.unknownCustomer"),
                when: when.full(dialogBooking, isStay(dialogBooking)),
              })
            : undefined
        }
        confirmLabel={t("bookings.confirmNoShow.confirm")}
        isPending={changeStatus.isPending}
        onConfirm={() => (dialogBooking ? void runStatus(dialogBooking, "no_show") : undefined)}
        onClose={() =>
          setDialog((current) => (current.kind === "noShow" ? { kind: "details", booking: current.booking } : current))
        }
      />

      <CustomerMessageModal
        open={dialog.kind === "message"}
        title={dialog.kind === "message" ? dialog.title : ""}
        text={dialog.kind === "message" ? dialog.text : ""}
        onClose={closeIf("message")}
      />
    </>
  );

  function detailActions(booking: BookingView) {
    const actions = bookingActions(booking.status);
    const editButton = (
      <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "edit", booking })}>
        {t("bookings.actions.edit")}
      </Button>
    );
    if (!Object.values(actions).some(Boolean)) {
      return (
        <div className="flex w-full flex-wrap justify-end gap-2">
          {editButton}
          <Button variant="secondary" size="sm" onClick={close}>
            {t("common.close")}
          </Button>
        </div>
      );
    }
    return (
      <div className="flex w-full flex-wrap justify-end gap-2" role="group" aria-label={t("bookings.actions.label")}>
        {actions.cancel ? (
          <Button variant="ghost" size="sm" className="text-danger! sm:mr-auto" onClick={() => openCancel(booking)}>
            {t("bookings.actions.cancel")}
          </Button>
        ) : null}
        {editButton}
        {actions.noShow ? (
          <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "noShow", booking })}>
            {t("bookings.actions.noShow")}
          </Button>
        ) : null}
        {actions.reschedule ? (
          <Button variant="secondary" size="sm" onClick={() => setDialog({ kind: "reschedule", booking })}>
            {t("bookings.actions.reschedule")}
          </Button>
        ) : null}
        {actions.complete ? (
          <Button variant="secondary" size="sm" isLoading={changeStatus.isPending} onClick={() => void runStatus(booking, "completed")}>
            {t("bookings.actions.complete")}
          </Button>
        ) : null}
        {actions.confirm ? (
          <Button size="sm" isLoading={changeStatus.isPending} onClick={() => void runStatus(booking, "confirmed")}>
            {t("bookings.actions.confirm")}
          </Button>
        ) : null}
      </div>
    );
  }
}
