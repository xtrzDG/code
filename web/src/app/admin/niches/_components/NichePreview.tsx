"use client";

/**
 * The profile questions as an owner sees them in the editor's language,
 * with the form's wording as it is typed (the code's text where the field
 * is left empty): label, required mark, hint and the choices.
 */

import { Card, Checkbox, Input, Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { LOCALE_DIRECTION, LOCALE_NATIVE_NAMES, isLocale } from "@/i18n/config";

import { shownText, type FormValues, type NicheTextEditor, type NicheTextField, type NicheTextQuestion } from "../_lib/nicheTexts";

export function NichePreview({ editor, values }: { editor: NicheTextEditor; values: FormValues }) {
  const { t } = useI18n();
  const language = editor.language;
  const fields = new Map(editor.fields.map((field) => [field.field_key, field]));
  const text = (fieldKey: string | null | undefined) => (fieldKey ? shownText(fields.get(fieldKey), values) : "");
  return (
    <Card
      aria-label={t("adminNiches.preview.title")}
      title={t("adminNiches.preview.title")}
      description={t("adminNiches.preview.description", {
        language: isLocale(language) ? LOCALE_NATIVE_NAMES[language] : language,
      })}
    >
      <ol className="space-y-5" lang={language} dir={isLocale(language) ? LOCALE_DIRECTION[language] : undefined}>
        {editor.questions.map((question) => (
          <li key={question.key} className="space-y-2">
            <p className="text-sm font-medium text-ink">
              {text(question.label_field)}
              {question.is_required ? (
                <span className="ms-1 text-danger" title={t("adminNiches.preview.required")}>
                  *
                </span>
              ) : null}
            </p>
            {question.hint_field ? <p className="text-xs text-ink-muted">{text(question.hint_field)}</p> : null}
            <Answer question={question} fields={fields} values={values} />
          </li>
        ))}
      </ol>
    </Card>
  );
}

function Answer({
  question,
  fields,
  values,
}: {
  question: NicheTextQuestion;
  fields: Map<string, NicheTextField>;
  values: FormValues;
}) {
  const { t } = useI18n();
  const choices = question.choices ?? [];
  if (choices.length === 0) {
    return <Input disabled aria-label={t("adminNiches.preview.answer")} placeholder={t("adminNiches.preview.answer")} />;
  }
  const Choice = question.answer_type === "multiple_choice" ? Checkbox : Radio;
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2">
      {choices.map((choice) => (
        <Choice
          key={choice.key}
          name={`preview-${question.key}`}
          disabled
          label={choice.field_key ? shownText(fields.get(choice.field_key), values) : (choice.fixed_label ?? choice.key)}
        />
      ))}
    </div>
  );
}
