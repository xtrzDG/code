"use client";

/**
 * Step 1 for a business that exists: its name (saved on Continue), its
 * kind (fixed) and the kind's required questions about the business, each
 * answer saved by itself a moment after it is given.
 */

import { useMemo, useState } from "react";

import { useNiches } from "@/api/catalog";
import { useBusiness } from "@/components/business/BusinessContext";
import { answersToSave, BUSINESS_QUESTION_STEPS, requiredQuestions, startingAnswers, wizardQuestions } from "@/lib/tunnel/questions";

import { BusinessStep, type BusinessForm } from "../steps/BusinessStep";
import { useAutosave } from "../useAutosave";
import type { StepContext } from "./stepContext";
import { useBusinessSave } from "./useBusinessSave";
import { useProfilePatch } from "./useProfilePatch";

export function BusinessScreen({ ctx }: { ctx: StepContext }) {
  const { business } = useBusiness();
  const niches = useNiches();
  const questions = useMemo(() => requiredQuestions(wizardQuestions(ctx.wizard), BUSINESS_QUESTION_STEPS), [ctx.wizard]);
  const [form, setForm] = useState<BusinessForm>(() => ({
    name: business.name,
    nicheKey: business.niche_key,
    answers: startingAnswers(questions),
  }));

  const patchProfile = useProfilePatch(ctx.businessId);
  const autosave = useAutosave(answersToSave(questions, form.answers), (answers) => patchProfile({ answers }));
  const businessSave = useBusinessSave(ctx.businessId);
  const [isSaving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    const saved = await autosave.flush();
    const name = form.name.trim();
    const renamed = name === business.name || (await businessSave.save(() => ({ name }))) !== null;
    setSaving(false);
    if (saved && renamed) {
      ctx.refresh();
      ctx.next();
    }
  };

  return (
    <BusinessStep
      form={form}
      onChange={setForm}
      niches={{ data: niches.data?.niches, error: niches.error, reload: niches.reload }}
      questions={questions}
      isNicheFixed
      onSubmit={() => void submit()}
      isBusy={isSaving}
    />
  );
}
