"use client";

import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useBusiness } from "@/components/business/BusinessContext";
import { CustomerName } from "@/components/insights/common";
import { ConfirmDialog } from "@/components/ui";
import { CustomerMessageModal } from "@/components/insights/CustomerMessageModal";
import { Modal, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { BookingsPage } from "../_lib/useBookingsPage";
import { BookingDetailActions } from "./BookingDetailActions";
import { BookingEditForm } from "./BookingEditForm";
import { BookingForm } from "./BookingForm";
import { BookingDetails, useBookingWhen } from "./BookingList";
import { CustomerLanguageSelect } from "./CustomerLanguageSelect";
import { RescheduleForm } from "./RescheduleForm";

/**
 * The bookings page's dialogs: a new booking, a booking's details with its
 * actions, editing, moving, cancelling (in the customer's language), a
 * no-show, and the text to send the customer afterwards.
 */
export function BookingDialogs({ page }: { page: BookingsPage }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const when = useBookingWhen();
  const { dialog, setDialog, dialogBooking, close, closeIf, isStay, replaceBooking, resources, defaultDate } = page;
  const { cancelLanguage, setCancelLanguage, runCancel, runStatus } = page;
  // "… the booking of {name} on {when}": the customer's name is user content.
  const aboutBooking = (key: "bookings.reschedule.description" | "bookings.confirmCancel.description" | "bookings.confirmNoShow.description") => {
    if (!dialogBooking) {
      return undefined;
    }
    const whenText = when.full(dialogBooking, isStay(dialogBooking));
    return dialogBooking.contact_name ? (
      <UserSentence text={t(key, { when: whenText })} values={{ name: dialogBooking.contact_name }} />
    ) : (
      t(key, { name: t("insights.unknownCustomer"), when: whenText })
    );
  };

  return (
    <>
      <Modal
        open={dialog.kind === "create"}
        onClose={closeIf("create")}
        title={t("bookings.form.title")}
        description={t("bookings.form.description")}
        size="lg"
      >
        <BookingForm
          resources={resources}
          defaultDate={defaultDate}
          initialValues={dialog.kind === "create" ? dialog.initial : undefined}
          onCancel={close}
          onCreated={(result) => {
            page.bookings.reload();
            queryCache.invalidate(queryKeys.bookings.grids(business.id));
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
        footer={dialogBooking ? <BookingDetailActions booking={dialogBooking} page={page} /> : undefined}
      >
        {dialogBooking ? <BookingDetails booking={dialogBooking} isStay={isStay(dialogBooking)} /> : null}
      </Modal>

      <Modal
        open={dialog.kind === "edit"}
        onClose={closeIf("edit")}
        title={t("bookings.edit.title")}
        description={aboutBooking("bookings.reschedule.description")}
      >
        {dialog.kind === "edit" ? (
          <BookingEditForm
            booking={dialog.booking}
            resources={resources}
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
        description={aboutBooking("bookings.reschedule.description")}
      >
        {dialog.kind === "reschedule" ? (
          <RescheduleForm
            booking={dialog.booking}
            isStay={isStay(dialog.booking)}
            onCancel={() => setDialog({ kind: "details", booking: dialog.booking })}
            onDone={(result) => {
              replaceBooking(result.booking);
              page.bookings.reload();
              toast.success(t("bookings.rescheduled"));
              setDialog({ kind: "message", title: t("bookings.rescheduled"), text: result.confirmation_text });
            }}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={dialog.kind === "cancel"}
        title={t("bookings.confirmCancel.title")}
        description={aboutBooking("bookings.confirmCancel.description")}
        confirmLabel={t("bookings.confirmCancel.confirm")}
        cancelLabel={t("bookings.confirmCancel.keep")}
        isPending={page.isCancelling}
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
        description={aboutBooking("bookings.confirmNoShow.description")}
        confirmLabel={t("bookings.confirmNoShow.confirm")}
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
}
