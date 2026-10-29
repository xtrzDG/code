"use client";

/**
 * What a search found. Self-serve: the numbers on offer and the monthly
 * price of any of them, each with "Take". Elsewhere: why our team arranges
 * the number (the regulator wants documents, or this server rents none of
 * that kind) and "Ask our team".
 */

import { IconPhone } from "@/components/icons";
import { Alert, Button } from "@/components/ui";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import { numberInText, teamArrangesReason, type PhoneNumberOffer, type PhoneNumberOffers } from "../../_lib/phoneLine";

export function NumberOffers({
  offers,
  onTake,
  onAskTeam,
  isAsking,
}: {
  offers: PhoneNumberOffers;
  onTake: (offer: PhoneNumberOffer) => void;
  onAskTeam: () => void;
  isAsking: boolean;
}) {
  const { t } = useI18n();
  const { money } = useBusinessFormat();
  const reason = teamArrangesReason(offers.availability);

  if (reason) {
    return (
      <Alert tone="info" title={t(reason)}>
        <Button variant="secondary" size="sm" className="mt-3" isLoading={isAsking} onClick={onAskTeam}>
          {t("phoneNumbers.request.ask")}
        </Button>
      </Alert>
    );
  }

  const list = offers.offers ?? [];
  const price = offers.monthly_price ? money(offers.monthly_price.money.amount_minor, offers.monthly_price.money.currency_code) : null;
  return (
    <section aria-labelledby="phone-offers-title" className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="phone-offers-title" className="text-sm font-semibold text-ink">
          {t("phoneNumbers.offers.title")}
        </h3>
        {price ? <p className="text-sm text-ink-muted">{t("phoneNumbers.offers.price", { price })}</p> : null}
      </div>
      {list.length === 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-ink-muted">{t("phoneNumbers.offers.none")}</p>
          <Button variant="secondary" size="sm" isLoading={isAsking} onClick={onAskTeam}>
            {t("phoneNumbers.request.ask")}
          </Button>
        </div>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line">
          {list.map((offer) => (
            <li key={offer.phone_number} className="flex items-center gap-3 px-4 py-3">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
                <IconPhone className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium tracking-wide text-ink" dir="ltr">
                  {offer.display_number}
                </p>
                {offer.locality || offer.region ? (
                  <p className="truncate text-xs text-ink-subtle">{[offer.locality, offer.region].filter(Boolean).join(", ")}</p>
                ) : null}
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onTake(offer)}
                aria-label={t("phoneNumbers.offers.takeLabel", { number: offer.display_number })}
              >
                {t("phoneNumbers.offers.take")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Taking one number: what it costs, what it becomes, how to give it back. */
export function TakeNumberConfirm({
  offer,
  offers,
  isTaking,
  onTake,
  onBack,
}: {
  offer: PhoneNumberOffer;
  offers: PhoneNumberOffers;
  isTaking: boolean;
  onTake: () => void;
  onBack: () => void;
}) {
  const { t } = useI18n();
  const { money } = useBusinessFormat();
  const price = offers.monthly_price ? money(offers.monthly_price.money.amount_minor, offers.monthly_price.money.currency_code) : "";
  return (
    <section aria-labelledby="phone-take-title" className="space-y-3 rounded-xl border border-accent/40 bg-accent-soft/40 p-4">
      <h3 id="phone-take-title" className="text-base font-semibold text-ink">
        {t("phoneNumbers.confirm.title", { number: numberInText(offer.display_number) })}
      </h3>
      <ul className="list-disc space-y-1 ps-5 text-sm text-ink-muted">
        <li>{t("phoneNumbers.confirm.price", { price })}</li>
        <li>{t("phoneNumbers.confirm.channel")}</li>
        <li>{t("phoneNumbers.confirm.giveBack")}</li>
      </ul>
      <div className="flex flex-wrap gap-2 pt-1">
        <Button onClick={onTake} isLoading={isTaking}>
          {t("phoneNumbers.confirm.take")}
        </Button>
        <Button variant="secondary" onClick={onBack} disabled={isTaking}>
          {t("phoneNumbers.confirm.back")}
        </Button>
      </div>
    </section>
  );
}
