"use client";

import { Fragment, useState } from "react";

import { useI18n } from "@/i18n/client";

import { splitConsentLine, type LegalDocumentKind } from "../_lib/legalConsent";
import { LegalDocumentDialog } from "./LegalDocumentDialog";

/**
 * "By continuing, you accept the Terms of Service and confirm you have
 * read the Privacy Policy." under the code step's button: continuing
 * accepts the version named by the sign-in options. Each document opens in
 * a dialog, so the code typed so far stays where it is.
 */
export function TermsLine({ termsVersion, privacyVersion }: { termsVersion: string; privacyVersion: string | null }) {
  const { t } = useI18n();
  const [open, setOpen] = useState<LegalDocumentKind | null>(null);
  const versions: Record<LegalDocumentKind, string | null> = {
    terms: termsVersion,
    privacy: privacyVersion,
    cookies: null,
  };

  return (
    <>
      <p className="text-center text-xs leading-relaxed text-ink-subtle" data-testid="terms-line">
        {splitConsentLine(t("legalConsent.line")).map((part, index) =>
          part.kind === "text" ? (
            <Fragment key={index}>{part.text}</Fragment>
          ) : (
            <button
              key={index}
              type="button"
              className="rounded-sm font-medium text-ink-muted underline decoration-line-strong underline-offset-2 transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              onClick={() => setOpen(part.document)}
            >
              {t(`legalConsent.${part.document}`)}
            </button>
          ),
        )}
      </p>
      <LegalDocumentDialog
        document={open}
        version={open === null ? null : versions[open]}
        onClose={() => setOpen(null)}
      />
    </>
  );
}
