"use client";

import { useId, useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { UserSentence } from "@/components/ui/UserContent";
import { bookingProblem, isPageProblem, type BookingProblem } from "@/lib/bookingPage/refusals";

import { MARKETING_CONSENT_TEXT_VERSION, marketingConsentTexts } from "./consentTexts";

type View = Schema<"ManagedBookingView">;

/**
 * The guest's consent to the business's marketing messages (Codice privacy
 * art. 130): an unticked box until they tick it themselves, with the
 * wording's version sent along so the consent stays provable. Unticking
 * takes it back as easily. The box shows what the API stored: a choice
 * that could not be saved goes back and says so; a link that stopped
 * working is the page's problem.
 */
export function MarketingConsentBox({
  view,
  language,
  onChanged,
  onProblem,
}: {
  view: View;
  language: string;
  onChanged: (next: View) => void;
  onProblem: (failure: BookingProblem) => void;
}) {
  const texts = marketingConsentTexts(language);
  const id = useId();
  const [pending, setPending] = useState<boolean | null>(null);
  const [hasFailed, setFailed] = useState(false);
  const isTicked = pending ?? view.marketing_consent;

  async function choose(isGiven: boolean) {
    setPending(isGiven);
    setFailed(false);
    try {
      const next = await unwrap(
        api.POST("/v1/public/bookings/{token}/marketing-consent", {
          params: { path: { token: view.token } },
          body: { is_given: isGiven, text_version: MARKETING_CONSENT_TEXT_VERSION },
        }),
      );
      onChanged(next);
    } catch (error) {
      const failure = bookingProblem(error);
      if (isPageProblem(failure)) {
        onProblem(failure);
      } else {
        setFailed(true);
      }
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="bp-section" data-testid="marketing-consent">
      <div className="flex items-start gap-3">
        <input
          id={`${id}-box`}
          type="checkbox"
          className="mt-0.5 size-5 shrink-0 accent-[color:var(--accent)]"
          checked={isTicked}
          disabled={pending !== null}
          aria-describedby={`${id}-note`}
          onChange={(event) => void choose(event.target.checked)}
        />
        <label htmlFor={`${id}-box`} className="text-[15px] text-ink">
          <UserSentence text={texts.label} values={{ business: view.business_name }} />
        </label>
      </div>
      <p id={`${id}-note`}>{texts.note}</p>
      {hasFailed ? (
        <p className="bp-problem" role="alert">
          {texts.failed}
        </p>
      ) : null}
    </section>
  );
}
