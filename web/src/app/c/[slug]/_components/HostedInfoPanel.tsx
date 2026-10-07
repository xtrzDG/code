import { capitalizeFirst, weekdayName } from "@/lib/format";
import { fillText, hostedInfoTexts, type HostedInfoTexts } from "@/lib/hostedChat/infoTexts";
import { businessClock, openState, weekRows, type OpenState } from "@/lib/hostedChat/openingHours";
import type { HostedChatView } from "@/server/hostedChat";

import { BookInChatButton } from "./BookInChatButton";
import { InfoDisclosure } from "./InfoDisclosure";

import "@/styles/hostedInfo.css";

const WEB_LINK = /^https?:\/\//i;

/** Hours, an address or a way to book: something to show beside the chat. */
export function hasHostedInfo(view: HostedChatView): boolean {
  return (view.hours?.length ?? 0) > 0 || Boolean(view.address) || view.takes_bookings || Boolean(view.booking_url);
}

function statusLine(state: OpenState, texts: HostedInfoTexts, language: string): string | null {
  switch (state.kind) {
    case "always":
      return texts.openAllDay;
    case "open":
      return `${texts.openNow} · ${fillText(texts.until, { time: state.closesAt })}`;
    case "closed": {
      const when =
        state.inDays === 0
          ? fillText(texts.opensAt, { time: state.opensAt })
          : state.inDays === 1
            ? fillText(texts.opensTomorrow, { time: state.opensAt })
            : fillText(texts.opensOn, { day: weekdayName(state.weekday, language), time: state.opensAt });
      return `${texts.closedNow} · ${when}`;
    }
    default:
      return null;
  }
}

/**
 * The hosted chat page as a link in bio: beside the chat (below its header
 * on phones) whether the business is open now, its week, its address with a
 * map link and a Book button: the business's own booking page when it has
 * one, else the chat. Everything is read on the business's clock.
 */
export function HostedInfoPanel({
  view,
  language,
  containerId,
  now,
}: {
  view: HostedChatView;
  language: string;
  containerId: string;
  now: Date;
}) {
  const texts = hostedInfoTexts(language);
  const hours = view.hours ?? [];
  const clock = businessClock(now, view.timezone ?? "UTC");
  const state = openState(hours, clock);
  const status = statusLine(state, texts, language);
  const rows = hours.length > 0 ? weekRows(hours, clock.weekday) : [];
  const mapsUrl = view.maps_url && WEB_LINK.test(view.maps_url) ? view.maps_url : null;
  const bookingUrl = view.booking_url && WEB_LINK.test(view.booking_url) ? view.booking_url : null;
  const isOpen = state.kind === "open" || state.kind === "always";

  return (
    <aside className="hc-info" aria-labelledby="hc-info-name">
      <div className="hc-info-head">
        <h2 id="hc-info-name" className="hc-info-name" dir="auto" data-user-content>
          {view.business_name}
        </h2>
        {status ? (
          <p className="hc-info-status" data-open={isOpen ? "true" : "false"}>
            <span className="hc-info-dot" aria-hidden />
            <span>{status}</span>
          </p>
        ) : null}
        {bookingUrl ? (
          <a className="hc-info-book" href={bookingUrl} target="_blank" rel="noopener noreferrer">
            {texts.book}
          </a>
        ) : view.takes_bookings ? (
          <BookInChatButton label={texts.book} prompt={texts.bookPrompt} containerId={containerId} />
        ) : null}
      </div>
      {rows.length > 0 || view.address ? (
        <InfoDisclosure label={texts.details}>
          {rows.length > 0 ? (
            <section className="hc-info-section">
              <h3>{texts.hours}</h3>
              <ul className="hc-hours">
                {rows.map((row) => (
                  <li key={row.weekday} aria-current={row.isToday ? "date" : undefined}>
                    <span>{capitalizeFirst(weekdayName(row.weekday, language), language)}</span>
                    {row.isAllDay || row.ranges.length === 0 ? (
                      <span>{row.isAllDay ? texts.openAllDay : texts.closed}</span>
                    ) : (
                      <span dir="ltr">{row.ranges.join(", ")}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {view.address ? (
            <section className="hc-info-section">
              <h3>{texts.address}</h3>
              <p dir="auto" data-user-content>
                {view.address}
              </p>
              {mapsUrl ? (
                <a className="hc-info-link" href={mapsUrl} target="_blank" rel="noopener noreferrer">
                  {texts.openMap}
                </a>
              ) : null}
            </section>
          ) : null}
        </InfoDisclosure>
      ) : null}
    </aside>
  );
}
