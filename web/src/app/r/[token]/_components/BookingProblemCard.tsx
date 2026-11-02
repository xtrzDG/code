/** Why the booking page cannot show the booking: the whole page is the explanation. */
export function BookingProblemCard({ title, text }: { title: string; text: string }) {
  return (
    <article className="bp-card bp-problem-page" aria-labelledby="bp-title">
      <span className="bp-mark" aria-hidden>
        <svg viewBox="0 0 24 24" focusable="false">
          <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
          <path d="M8 3v4M16 3v4M3.5 10h17M10 14l4 4M14 14l-4 4" />
        </svg>
      </span>
      <h1 id="bp-title" className="bp-title">
        {title}
      </h1>
      <p>{text}</p>
    </article>
  );
}
