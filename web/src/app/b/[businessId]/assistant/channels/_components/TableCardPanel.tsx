"use client";

import { useMemo, useRef, useState } from "react";

import { IconFile } from "@/components/icons";
import { Button, Field, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { directionOf } from "@/lib/hostedChat/language";
import { hostedChatTexts } from "@/lib/hostedChat/texts";
import { languageName } from "@/lib/format";

import type { QrMatrix } from "../_lib/qrCode";
import { buildTableCardHtml, printFrame } from "../_lib/tableCard";
import { useShareMark } from "../_lib/useShareMark";

/** A6 at 96 CSS pixels per inch: 105 × 148 mm. */
const CARD_WIDTH_PX = 397;
const CARD_HEIGHT_PX = 559;
const PREVIEW_SCALE = 0.5;

/**
 * The printable A6 table card in one of the business's languages: a
 * preview (the card itself, scaled down in a frame) and "Print", which
 * prints that frame.
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

  const html = useMemo(() => {
    const texts = hostedChatTexts(language);
    return buildTableCardHtml({
      businessName,
      linkText,
      matrix,
      language,
      direction: directionOf(language),
      accent,
      heading: texts.scanToChat,
      hint: texts.cardHint,
    });
  }, [accent, businessName, language, linkText, matrix]);

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
          className="pointer-events-none origin-top-left border-0 bg-white"
          style={{ width: CARD_WIDTH_PX, height: CARD_HEIGHT_PX, transform: `scale(${PREVIEW_SCALE})` }}
        />
      </div>
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
