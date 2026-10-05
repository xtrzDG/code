import type { Schema } from "@/api/types";
import { bookingWhen } from "@/lib/bookingPage/format";
import type { BookingPageTexts } from "@/lib/bookingPage/texts";
import { formatNumber } from "@/lib/format";
import { formatPhone } from "@/lib/phone";

const WEB_LINK = /^https?:\/\//i;

/**
 * What the booking is: when (the visit, or a stay's arrival and departure),
 * how many guests, the service, where (with a map link) and the phone,
 * unless the ways to write list a call already.
 */
export function BookingFacts({
  view,
  texts,
  language,
}: {
  view: Schema<"ManagedBookingView">;
  texts: BookingPageTexts;
  language: string;
}) {
  const when = bookingWhen(view, language);
  const mapsUrl = view.maps_url && WEB_LINK.test(view.maps_url) ? view.maps_url : null;
  const listsCall = (view.chat_links ?? []).some((link) => link.kind === "phone");

  return (
    <dl className="bp-facts">
      {when.departure ? (
        <>
          <div className="bp-fact">
            <dt>{texts.arrival}</dt>
            <dd>{when.date}</dd>
          </div>
          <div className="bp-fact">
            <dt>{texts.departure}</dt>
            <dd>{when.departure}</dd>
          </div>
        </>
      ) : (
        <div className="bp-fact bp-fact-when">
          <dt>{texts.when}</dt>
          <dd>
            <span>{when.date}</span>
            {when.times ? (
              <span className="bp-time">
                <bdi>{when.times}</bdi>
              </span>
            ) : null}
          </dd>
        </div>
      )}
      <div className="bp-fact">
        <dt>{texts.guests}</dt>
        <dd>{formatNumber(view.party_size, language)}</dd>
      </div>
      {view.service_title ? (
        <div className="bp-fact">
          <dt>{texts.service}</dt>
          <dd dir="auto">{view.service_title}</dd>
        </div>
      ) : null}
      {view.address ? (
        <div className="bp-fact bp-fact-wide">
          <dt>{texts.address}</dt>
          <dd>
            <span dir="auto">{view.address}</span>
            {mapsUrl ? (
              <a className="bp-link" href={mapsUrl} target="_blank" rel="noopener noreferrer">
                {texts.openMap}
              </a>
            ) : null}
          </dd>
        </div>
      ) : null}
      {view.phone_number && !listsCall ? (
        <div className="bp-fact">
          <dt>{texts.phone}</dt>
          <dd>
            <a className="bp-link" href={`tel:${view.phone_number}`} dir="ltr">
              {formatPhone(view.phone_number)}
            </a>
          </dd>
        </div>
      ) : null}
    </dl>
  );
}
