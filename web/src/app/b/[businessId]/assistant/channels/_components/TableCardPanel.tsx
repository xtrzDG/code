"use client";

import { useId, useMemo, useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconFile } from "@/components/icons";
import { useReferralProgram } from "@/components/referrals/useReferralProgram";
import { Button, Field, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { directionOf } from "@/lib/hostedChat/language";
import { hostedChatTexts } from "@/lib/hostedChat/texts";
import { languageName } from "@/lib/format";
import { poweredByText } from "@/lib/referrals/poweredByTexts";
import { linkWithSource, withPoweredByFooter } from "@/lib/referrals/referralLinks";

import type { QrMatrix } from "../_lib/qrCode";
import { buildTableCardHtml, printFrame } from "../_lib/tableCard";
import { useShareMark } from "../_lib/useShareMark";

/** A6 at 96 CSS pixels per inch: 105 × 148 mm. */
const CARD_WIDTH_PX = 397;
const CARD_HEIGHT_PX = 559;
const PREVIEW_SCALE = 0.5;

/** The `src` tag of sign-ups that came from the printed card's "Powered by" line. */
const CARD_SOURCE = "table_card";

/**
 * The printable A6 table card in one of the business's languages: a
 * preview (the card itself, scaled down in a frame) and "Print", which
 * prints that frame. Its foot carries "Powered by" with the business's
 * referral code, which a Plus owner may switch off (for the chat and the
 * chat page too).
 */
export function TableCardPanel({
  matrix,
  linkText,
  accent,
  businessName,
  languages,
  defaultLanguage,
}: {
  matrix: QrMatrix;
  linkText: string;
  accent: string | null;
  businessName: string;
  languages: readonly string[];
  defaultLanguage: string;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const frame = useRef<HTMLIFrameElement>(null);
  const markShared = useShareMark();
  const choices = languages.length > 0 ? languages : [defaultLanguage];
  const [language, setLanguage] = useState(choices.includes(defaultLanguage) ? defaultLanguage : (choices[0] ?? "en"));
  const { business, isOwner } = useBusiness();
  const { program, setPoweredByHidden, poweredByChange } = useReferralProgram(business.id, { enabled: isOwner });
  const poweredBy = program.data?.powered_by ?? null;
  const poweredByUrl = poweredBy?.url ? linkWithSource(poweredBy.url, CARD_SOURCE) : null;
  const hintId = useId();

  const html = useMemo(() => {
    const texts = hostedChatTexts(language);
    const card = buildTableCardHtml({
      businessName,
      linkText,
      matrix,
      language,
      direction: directionOf(language),
      accent,
      heading: texts.scanToChat,
      hint: texts.cardHint,
    });
    return withPoweredByFooter(card, poweredByText(language), poweredByUrl);
  }, [accent, businessName, language, linkText, matrix, poweredByUrl]);

  return (
    <div className="space-y-3 border-t border-line pt-5">
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-ink">{t("share.cardTitle")}</h3>
        <p className="text-sm text-ink-muted">{t("share.cardHint")}</p>
      </div>
      {choices.length > 1 ? (
        <Field label={t("share.cardLanguage")}>
          {(control) => (
            <Select {...control} className="max-w-xs" value={language} onChange={(event) => setLanguage(event.target.value)}>
              {choices.map((tag) => (
                <option key={tag} value={tag}>
                  {languageName(tag, locale)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : null}
      <div
        className="mx-auto overflow-hidden rounded-lg shadow-md ring-1 ring-line"
        style={{ width: CARD_WIDTH_PX * PREVIEW_SCALE, height: CARD_HEIGHT_PX * PREVIEW_SCALE }}
      >
        <iframe
          ref={frame}
          title={t("share.cardPreview")}
          srcDoc={html}
          tabIndex={-1}
          data-testid="table-card-preview"
          className="pointer-events-none origin-top-left border-0 bg-white rtl:origin-top-right"
          style={{ width: CARD_WIDTH_PX, height: CARD_HEIGHT_PX, transform: `scale(${PREVIEW_SCALE})` }}
        />
      </div>
      {poweredBy ? (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-line p-3">
          <div className="min-w-0 space-y-0.5">
            <p className="text-sm font-medium text-ink">{t("referrals.poweredBy.title")}</p>
            <p id={hintId} className="text-xs text-ink-muted">
              {!poweredBy.is_removable
                ? t("referrals.poweredBy.plusOnly")
                : poweredBy.is_shown
                  ? t("referrals.poweredBy.description")
                  : t("referrals.poweredBy.hidden")}
            </p>
          </div>
          <Switch
            checked={poweredBy.is_shown}
            label={t("referrals.poweredBy.toggle")}
            describedBy={hintId}
            disabled={!poweredBy.is_removable || poweredByChange.isPending}
            onChange={(checked) => {
              void setPoweredByHidden(!checked).then((ok) => {
                if (ok) {
                  toast.success(t("referrals.poweredBy.saved"));
                }
              });
            }}
          />
        </div>
      ) : null}
      <div className="flex justify-center">
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconFile className="size-4" aria-hidden />}
          onClick={() => {
            if (printFrame(frame.current)) {
              markShared("printed_qr");
            } else {
              toast.info(t("share.printFailed"));
            }
          }}
        >
          {t("share.printCard")}
        </Button>
      </div>
    </div>
  );
}
