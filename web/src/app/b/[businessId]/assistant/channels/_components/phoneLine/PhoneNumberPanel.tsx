"use client";

/**
 * The phone card's own part: the number the business rents from us (its
 * place, monthly price and whether it answers yet), an open request to our
 * team, or "Get a number". Shown on the phone channel card and in the setup
 * tunnel's channels step. A rented number goes back when the phone channel
 * is disconnected.
 */

import { useState } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPhone } from "@/components/icons";
import { Badge, Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryName } from "@/lib/countries";

import { numberInText, rentedNumberState, type PhoneNumberRequest, type RentedPhoneNumber } from "../../_lib/phoneLine";
import { usePhoneLine, usePhoneLineActions } from "../../_lib/usePhoneLine";
import { GetNumberDialog } from "./GetNumberDialog";

export function PhoneNumberPanel({
  canManage,
  showGetNumber = true,
  onChanged,
}: {
  canManage: boolean;
  /** False while the phone channel is connected with the business's own number. */
  showGetNumber?: boolean;
  /** After a number was taken (the phone channel is now connected). */
  onChanged?: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const line = usePhoneLine(business.id);
  const actions = usePhoneLineActions(business.id);
  const [isOpen, setOpen] = useState(false);
  const data = line.data;
  if (!data) {
    return null;
  }

  if (data.rented_number) {
    return <RentedNumber number={data.rented_number} />;
  }
  if (data.open_request) {
    return (
      <OpenRequest
        request={data.open_request}
        canManage={canManage}
        isCancelling={actions.cancel.isPending}
        onCancel={async () => {
          const result = await actions.cancel.run();
          if (result.ok) {
            toast.success(t("phoneNumbers.panel.requestCancelled"));
          }
        }}
      />
    );
  }
  if (!showGetNumber) {
    return null;
  }

  return (
    <div className="mt-4 space-y-3 rounded-xl border border-dashed border-line-strong px-4 py-3">
      <p className="text-sm text-ink-muted">{t("phoneNumbers.panel.noNumber")}</p>
      {canManage ? (
        <Button size="sm" variant="secondary" leadingIcon={<IconPhone className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
          {t("phoneNumbers.panel.getNumber")}
        </Button>
      ) : (
        <p className="text-xs text-ink-subtle">{t("phoneNumbers.panel.ownerOnly")}</p>
      )}
      {isOpen ? (
        <GetNumberDialog
          open={isOpen}
          onClose={() => setOpen(false)}
          businessId={business.id}
          line={data}
          onRented={(number) => {
            setOpen(false);
            toast.success(t("phoneNumbers.confirm.done", { number: numberInText(number.display_number) }));
            onChanged?.();
          }}
          onRequested={() => {
            setOpen(false);
            toast.success(t("phoneNumbers.request.sent"));
          }}
        />
      ) : null}
    </div>
  );
}

function RentedNumber({ number }: { number: RentedPhoneNumber }) {
  const { t, locale } = useI18n();
  const { money } = useBusinessFormat();
  const price = money(number.monthly_price.money.amount_minor, number.monthly_price.money.currency_code);
  const place = [number.locality, countryName(number.country_code, locale)].filter(Boolean).join(", ");
  const state = rentedNumberState(number);
  return (
    <section aria-label={t("phoneNumbers.panel.rentedTitle")} className="mt-4 space-y-2 rounded-xl border border-line bg-surface-muted/60 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-ink-subtle">{t("phoneNumbers.panel.rentedTitle")}</p>
        <Badge tone={state === "phoneNumbers.panel.answering" ? "success" : "neutral"}>{t(state)}</Badge>
      </div>
      <p className="text-lg font-semibold tracking-wide text-ink" dir="ltr">
        {number.display_number}
      </p>
      <p className="text-sm text-ink-muted">
        {place} · {t("phoneNumbers.panel.monthly", { price })}
      </p>
      {number.status === "active" ? <p className="text-xs text-ink-subtle">{t("phoneNumbers.panel.giveBackHint")}</p> : null}
    </section>
  );
}

function OpenRequest({
  request,
  canManage,
  isCancelling,
  onCancel,
}: {
  request: PhoneNumberRequest;
  canManage: boolean;
  isCancelling: boolean;
  onCancel: () => void;
}) {
  const { t, locale } = useI18n();
  const values = {
    type: t(`phoneNumbers.types.${request.number_type}`),
    country: countryName(request.country_code, locale),
    city: request.city ?? "",
  };
  return (
    <section aria-label={t("phoneNumbers.panel.requestTitle")} className="mt-4 space-y-2 rounded-xl border border-line bg-info-soft/60 px-4 py-3">
      <p className="text-sm font-semibold text-ink">{t("phoneNumbers.panel.requestTitle")}</p>
      <p className="text-sm text-ink-muted">
        {request.city ? t("phoneNumbers.panel.requestTextCity", values) : t("phoneNumbers.panel.requestText", values)}
      </p>
      {canManage ? (
        <Button size="sm" variant="ghost" isLoading={isCancelling} onClick={onCancel}>
          {t("phoneNumbers.panel.cancelRequest")}
        </Button>
      ) : null}
    </section>
  );
}
