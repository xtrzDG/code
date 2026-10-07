"use client";

/**
 * "Business" in Assistant → Business profile: the first screen of the
 * tunnel in the edit mode. The name, the kind (fixed), every niche question
 * about the business and the links the assistant may send, each saved by
 * itself as the owner types.
 */

import { useMemo, useState } from "react";

import { useNiches } from "@/api/catalog";
import { useBusiness } from "@/components/business/BusinessContext";
import { answersPatch } from "@/lib/profile/answers";
import { linkProblems, linkRowsFrom, linksPayload, type LinkRow } from "@/lib/profile/links";
import { sectionQuestions } from "@/lib/profile/sections";
import { startingAnswers } from "@/lib/tunnel/questions";
import { validateAnswers } from "@/lib/wizard/answers";

import { useBusinessSave } from "../flow/useBusinessSave";
import type { StepContext } from "../flow/stepContext";
import { BusinessStep, type BusinessForm } from "../steps/BusinessStep";
import { LinksField } from "./LinksField";
import { SaveProblem } from "./SaveProblem";
import { useBusinessField } from "./useBusinessField";
import { useProfileField } from "./useProfileField";

export function BusinessEdit({ ctx }: { ctx: StepContext }) {
  const { business } = useBusiness();
  const niches = useNiches();
  const questions = useMemo(() => sectionQuestions(ctx.wizard, "business"), [ctx.wizard]);
  const [form, setForm] = useState<BusinessForm>(() => ({ name: business.name, nicheKey: business.niche_key, answers: startingAnswers(questions) }));
  const [links, setLinks] = useState<LinkRow[]>(() => linkRowsFrom(ctx.wizard.profile.links));

  const businessSave = useBusinessSave(ctx.businessId);
  const name = form.name.trim();
  useBusinessField(businessSave, name, (value) => ({ name: value }), { isValid: (value) => value !== "" });

  const answerProblems = validateAnswers(questions, form.answers);
  const answers = useProfileField(ctx.businessId, answersPatch(questions, form.answers), (value) => ({ answers: value }), {
    isValid: () => Object.keys(answerProblems).length === 0,
  });

  const problems = linkProblems(links);
  const linksSave = useProfileField(ctx.businessId, linksPayload(links), (value) => ({ links: value }), {
    isValid: () => Object.keys(problems).length === 0,
  });

  return (
    <BusinessStep
      mode="edit"
      form={form}
      onChange={setForm}
      niches={{ data: niches.data?.niches, error: niches.error, reload: niches.reload }}
      questions={questions}
      isNicheFixed
      onSubmit={() => undefined}
      problems={{ name: name === "" ? "tunnelBusiness.business.errors.name" : undefined, answers: answerProblems }}
      extra={
        <>
          <SaveProblem error={answers.error} />
          <LinksField rows={links} onChange={setLinks} problems={problems} error={linksSave.error} />
        </>
      }
    />
  );
}
