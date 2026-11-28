"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronDown, IconInfo, IconPhone } from "@/components/icons";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

import { forwardingCodeRows } from "../_lib/forwardingCodes";
import { usePhoneLine } from "../_lib/usePhoneLine";
import { ForwardingCodeList } from "./ForwardingCodeList";

type CarrierInstructions = Schema<"CarrierForwardingInstructions">;

/**
 * Forwarding of missed, busy and unreachable calls to the assistant's number:
 * steps and codes in the interface language. Usually the standard GSM codes
 * come first and the codes of named operators after them. Where carriers take
 * codes of their own (`is_carrier_choice_needed`: the United States), the
 * owner opens their carrier first (its GSM codes and star codes, such as
 * Verizon's *71) and the standard codes follow for carriers not listed, as
 * the steps say.
 */
export function CallForwardingCard() {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const instructions = useQuery(queryKeys.channels.callForwarding(business.id, locale), () =>
    api.GET("/v1/businesses/{business_id}/call-forwarding-instructions", {
      params: { path: { business_id: business.id }, query: { language: locale } },
    }),
  );
  const data = instructions.data;
  // A number rented from us: the forwarding target is that number, billed monthly.
  const rented = usePhoneLine(business.id).data?.rented_number;
  const { money } = useBusinessFormat();

  return (
    <Card title={t("channels.forwarding.title")} description={t("channels.forwarding.description")}>
      {instructions.error && !data ? (
        <ErrorState error={instructions.error} onRetry={instructions.reload} className="py-6" />
      ) : !data ? (
        <LoadingRegion label={t("common.loading")} className="py-1"><SkeletonText lines={4} /></LoadingRegion>
      ) : (
        <div className="space-y-6" lang={data.display_language}>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-muted/60 px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="flex size-9 items-center justify-center rounded-full bg-accent-soft text-accent" aria-hidden>
                <IconPhone className="size-5" />
              </span>
              <div>
                <p className="text-xs text-ink-subtle">{t("channels.forwarding.assistantNumber")}</p>
                <p className="text-lg font-semibold tracking-wide text-ink" dir="ltr">
                  {data.assistant_phone_number_display}
                </p>
                {rented && rented.phone_number === data.assistant_phone_number ? (
                  <p className="text-xs text-ink-subtle">
                    {t("phoneNumbers.panel.rentedTitle")} ·{" "}
                    {t("phoneNumbers.panel.monthly", {
                      price: money(rented.monthly_price.money.amount_minor, rented.monthly_price.money.currency_code),
                    })}
                  </p>
                ) : null}
              </div>
            </div>
            <CopyButton value={data.assistant_phone_number} />
          </div>

          <section aria-labelledby="forwarding-steps" className="space-y-2">
            <h3 id="forwarding-steps" className="text-sm font-semibold text-ink">
              {t("channels.forwarding.stepsTitle")}
            </h3>
            <ol className="list-decimal space-y-1.5 ps-5 text-sm text-ink-muted marker:font-medium marker:text-ink-subtle">
              {data.steps.map((step, index) => (
                <li key={index}>{step}</li>
              ))}
            </ol>
          </section>

          {data.is_carrier_choice_needed ? (
            <>
              <CarrierCodes title={t("channels.forwarding.chooseCarrierTitle")} carriers={data.carriers ?? []} />
              <StandardCodes title={t("channels.forwarding.otherCarriersTitle")} codes={data.codes} />
            </>
          ) : (
            <>
              <StandardCodes title={t("channels.forwarding.codesTitle")} codes={data.codes} />
              <CarrierCodes title={t("channels.forwarding.carriersTitle")} carriers={data.carriers ?? []} />
            </>
          )}

          {data.notes && data.notes.length > 0 ? (
            <section aria-labelledby="forwarding-notes" className="rounded-xl bg-info-soft/70 p-4">
              <h3 id="forwarding-notes" className="flex items-center gap-2 text-sm font-semibold text-info">
                <IconInfo className="size-4" aria-hidden />
                {t("channels.forwarding.notesTitle")}
              </h3>
              <ul className="mt-2 list-disc space-y-1 ps-5 text-sm text-ink-muted">
                {data.notes.map((note, index) => (
                  <li key={index}>{note}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </Card>
  );
}

/** The top-level codes: the standard ones, or (with a carrier to choose) those for carriers not listed. */
function StandardCodes({ title, codes }: { title: string; codes: readonly Schema<"CallForwardingCode">[] }) {
  return (
    <section aria-labelledby="forwarding-codes" className="space-y-2">
      <h3 id="forwarding-codes" className="text-sm font-semibold text-ink">
        {title}
      </h3>
      <ForwardingCodeList rows={forwardingCodeRows(codes)} />
    </section>
  );
}

/** Each named carrier, folded: what is known of it, then its GSM codes and star codes (either may be none). */
function CarrierCodes({ title, carriers }: { title: string; carriers: readonly CarrierInstructions[] }) {
  if (carriers.length === 0) {
    return null;
  }
  return (
    <section aria-labelledby="forwarding-carriers" className="space-y-2">
      <h3 id="forwarding-carriers" className="text-sm font-semibold text-ink">
        {title}
      </h3>
      <div className="divide-y divide-line rounded-xl border border-line">
        {carriers.map((carrier) => {
          const rows = forwardingCodeRows(carrier.codes, carrier.star_codes);
          return (
            <details key={carrier.carrier_name} className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-ink hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus [&::-webkit-details-marker]:hidden">
                {carrier.carrier_name}
                <IconChevronDown className="size-4 text-ink-subtle transition-transform group-open:rotate-180" aria-hidden />
              </summary>
              <div className="space-y-3 px-4 pb-4">
                {carrier.note ? <p className="text-sm text-ink-muted">{carrier.note}</p> : null}
                {rows.length > 0 ? <ForwardingCodeList rows={rows} /> : null}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
