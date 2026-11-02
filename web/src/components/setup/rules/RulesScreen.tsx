"use client";

/**
 * "Rules" of Assistant → Business profile, in the edit mode of the
 * tunnel's screens: the ready answers, when to call a person, what never
 * to promise, the tone and the niche's questions about how the business
 * works. Everything saves itself as the owner types; the niche's starter
 * answers are only offered, never saved until the owner takes them. Whether
 * calls are recorded (and so whether callers hear it) is set in Settings →
 * Calls, which the screen links to.
 */

import Link from "next/link";
import { useId, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { cleanRules } from "@/lib/wizard/faq";

import { SaveProblem } from "../edit/SaveProblem";
import { SectionQuestions } from "../edit/SectionQuestions";
import { useProfileField } from "../edit/useProfileField";
import type { StepContext } from "../flow/stepContext";
import { StepScreen } from "../StepScreen";
import { FaqList } from "./FaqList";
import { RuleList } from "./RuleList";
import { useFaqRows } from "./useFaqRows";

const MAX_TONE_LENGTH = 200;

export function RulesScreen({ ctx }: { ctx: StepContext }) {
  const { t, locale } = useI18n();
  const toneId = useId();
  const { profile } = ctx.wizard;
  const { starters } = ctx;
  const faq = useFaqRows(ctx.businessId);
  const gaps = useQuery(queryKeys.profile.gaps(ctx.businessId, locale), () =>
    api.GET("/v1/businesses/{business_id}/profile/gaps", { params: { path: { business_id: ctx.businessId }, query: { language: locale } } }),
  );

  const [handoff, setHandoff] = useState<string[]>(() => profile.handoff_rules ?? []);
  const [forbidden, setForbidden] = useState<string[]>(() => profile.forbidden ?? []);
  const [tone, setTone] = useState(profile.tone ?? "");
  const handoffSave = useProfileField(ctx.businessId, cleanRules(handoff), (value) => ({ handoff_rules: value }));
  const forbiddenSave = useProfileField(ctx.businessId, cleanRules(forbidden), (value) => ({ forbidden: value }));
  const toneSave = useProfileField(ctx.businessId, tone.trim(), (value) => ({ tone: value || null }));

  const handoffSuggestions = starters.handoff_rules?.length ? starters.handoff_rules : ctx.wizard.default_handoff_rules;
  const forbiddenSuggestions = starters.forbidden_rules?.length ? starters.forbidden_rules : ctx.wizard.default_forbidden_rules;
  const suggestedTone = tone.trim() === "" && starters.tone ? starters.tone : null;

  return (
    <StepScreen mode="edit" title={t("profileEdit.sections.rules.title")} text={t("profileEdit.sections.rules.text")} wide actions={{}}>
      <div className="space-y-6">
        <FaqList faq={faq} starters={starters.faq ?? []} gaps={gaps.data?.gaps ?? []} />
        <RuleList
          title={t("profileEdit.rules.handoffTitle")}
          hint={t("profileEdit.rules.handoffHint")}
          rules={handoff}
          onChange={setHandoff}
          suggestions={handoffSuggestions}
          error={handoffSave.error}
        />
        <RuleList
          title={t("profileEdit.rules.forbiddenTitle")}
          hint={t("profileEdit.rules.forbiddenHint")}
          rules={forbidden}
          onChange={setForbidden}
          suggestions={forbiddenSuggestions}
          error={forbiddenSave.error}
        />
        {/* What the API accepts as an owner's rule and the tone: shown once, before the tone. */}
        <p className="text-sm text-ink-muted">{t("profileEdit.rules.instructionRule")}</p>
        <section aria-labelledby={toneId} className="space-y-5 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
          <h2 id={toneId} className="sr-only">
            {t("profileEdit.rules.toneTitle")}
          </h2>
          <Field label={t("profileEdit.rules.toneTitle")} optionalLabel={t("common.optional")}>
            {(control) => (
              <Input
                {...control}
                value={tone}
                maxLength={MAX_TONE_LENGTH}
                placeholder={t("profileEdit.rules.tonePlaceholder")}
                onChange={(event) => setTone(event.target.value)}
              />
            )}
          </Field>
          {suggestedTone ? (
            <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
              {t("profileEdit.rules.toneSuggested", { tone: suggestedTone })}
              <Button variant="ghost" size="sm" onClick={() => setTone(suggestedTone)}>
                {t("profileEdit.rules.useTone")}
              </Button>
            </p>
          ) : null}
          <SaveProblem error={toneSave.error} />
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
            {t("profileEdit.rules.recordingNotice")}
            <Link
              href={businessPath(ctx.businessId, "settings/calls")}
              className="inline-flex min-h-10 shrink-0 items-center rounded-lg px-2 text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-focus"
            >
              {t("profileEdit.rules.recordingNoticeLink")}
            </Link>
          </p>
        </section>
        <SectionQuestions ctx={ctx} section="rules" title={t("profileEdit.rules.questionsTitle")} />
      </div>
    </StepScreen>
  );
}
