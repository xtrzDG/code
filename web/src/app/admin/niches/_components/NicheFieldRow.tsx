"use client";

import { Field, Input, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { LOCALE_DIRECTION, isLocale } from "@/i18n/config";

import { fieldCaption, problemMessage, textProblem, type NicheTextField } from "../_lib/nicheTexts";

/** Long texts (descriptions, answers) get a few lines to write in; still one line of text. */
const LONG_TEXT_LENGTH = 300;

/**
 * One editable text: what it is, the code's wording owners read today
 * (English when the code has none in this language), and the admin's own
 * wording, written in the editor's language and direction.
 */
export function NicheFieldRow({
  field,
  language,
  value,
  onChange,
}: {
  field: NicheTextField;
  language: string;
  value: string;
  onChange: (fieldKey: string, value: string) => void;
}) {
  const { t } = useI18n();
  const [captionKey, captionValues] = fieldCaption(field.field_key);
  const problem = textProblem(field, value);
  const direction = isLocale(language) ? LOCALE_DIRECTION[language] : "ltr";
  const code = field.code_text
    ? t("adminNiches.editor.code", { text: field.code_text })
    : t("adminNiches.editor.codeInEnglish", { text: field.english_text });
  const controlProps = {
    value,
    lang: language,
    dir: direction,
    autoComplete: "off",
  } as const;

  return (
    <Field
      label={t(captionKey, captionValues)}
      hint={
        <>
          <span className="block text-ink" lang={field.code_text ? language : "en"} dir="auto">
            {code}
          </span>
          <span className="block">{t("adminNiches.editor.newWordingHint", { max: field.max_length })}</span>
        </>
      }
      error={problem ? t(...problemMessage(problem)) : undefined}
    >
      {(control) =>
        field.max_length > LONG_TEXT_LENGTH ? (
          <Textarea
            {...control}
            {...controlProps}
            rows={2}
            onChange={(event) => onChange(field.field_key, event.target.value)}
          />
        ) : (
          <Input {...control} {...controlProps} onChange={(event) => onChange(field.field_key, event.target.value)} />
        )
      }
    </Field>
  );
}
