"use client";

/**
 * The first two steps of the tunnel before the business exists (/create):
 * the answers live in a draft in this browser (a reload or tomorrow
 * continues them), and leaving "Where are you?" creates the assistant in
 * one call (POST /v1/assistants: the business with its country's defaults)
 * and saves the address and first answers to its profile; then the tunnel
 * goes on at /b/{id}/setup.
 */

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { queryKeys } from "@/api/queryKeys";
import { CATALOG_STALE_MS, useNiches } from "@/api/catalog";
import type { CurrentUserView, NicheKey, RequestBody } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { setupPath } from "@/lib/navigation";
import { browserStorage, clearDraft, EMPTY_DRAFT, readDraft, writeDraft, type CreateDraft } from "@/lib/tunnel/draft";
import { answersToSave, BUSINESS_QUESTION_STEPS, catalogQuestions, requiredQuestions } from "@/lib/tunnel/questions";

import { usePlace } from "../usePlace";

export function useCreateFlow(me: CurrentUserView) {
  const { locale } = useI18n();
  const router = useRouter();
  const userId = me.user.id;
  const [draft, setDraft] = useState<CreateDraft>(() => readDraft(browserStorage(), userId) ?? EMPTY_DRAFT);
  const [isFinishing, setFinishing] = useState(false);

  // Every change is kept in this browser until the business exists.
  useEffect(() => {
    writeDraft(browserStorage(), userId, draft);
  }, [draft, userId]);

  const niches = useNiches();
  const niche = niches.data?.niches.find((item) => item.key === draft.nicheKey);
  const details = useQuery(
    queryKeys.catalog.niche(draft.nicheKey, locale),
    () => api.GET("/v1/catalog/niches/{niche_key}", { params: { path: { niche_key: draft.nicheKey as NicheKey }, query: { language: locale } } }),
    { enabled: draft.nicheKey !== "", staleMs: CATALOG_STALE_MS },
  );
  const questions = useMemo(
    () =>
      details.data && details.data.niche.key === draft.nicheKey
        ? requiredQuestions(catalogQuestions(details.data.questions ?? []), BUSINESS_QUESTION_STEPS)
        : null,
    [details.data, draft.nicheKey],
  );
  const place = usePlace(draft, me.user.country_code);

  const create = useMutation(
    (body: RequestBody<"/v1/assistants", "post">) => api.POST("/v1/assistants", { body }),
    { errorMessages: { access_denied: "tunnelBusiness.place.errors.restricted" } },
  );
  const saveProfile = useMutation(
    (businessId: string, body: RequestBody<"/v1/businesses/{business_id}/profile", "patch">) =>
      api.PATCH("/v1/businesses/{business_id}/profile", { params: { path: { business_id: businessId } }, body }),
    { errorToast: false },
  );

  /** Create the assistant from the draft and go on in its own setup. */
  const finish = async (): Promise<void> => {
    if (!place.countryCode || !place.defaults) {
      return;
    }
    setFinishing(true);
    const created = await create.run({
      name: draft.name.trim(),
      niche_key: draft.nicheKey as NicheKey,
      country_code: place.countryCode,
      ...(draft.city.trim() ? { city: draft.city.trim() } : {}),
      ...(place.timezone ? { timezone: place.timezone } : {}),
      languages: place.languages,
      ...(place.defaultLanguage ? { default_language: place.defaultLanguage } : {}),
    });
    if (!created.ok) {
      setFinishing(false);
      return;
    }
    const businessId = created.data.business.id;
    const answers = questions ? answersToSave(questions, draft.answers) : [];
    const address = draft.address.trim();
    if (answers.length > 0 || address) {
      // The business exists either way: a failed save is asked again on its screen.
      await saveProfile.run(businessId, { ...(address ? { address: { text: address } } : {}), ...(answers.length > 0 ? { answers } : {}) });
    }
    clearDraft(browserStorage(), userId);
    router.replace(setupPath(businessId, "offer"));
  };

  return {
    draft,
    setDraft,
    niches,
    niche,
    questions: draft.nicheKey ? questions : [],
    place,
    finish,
    isFinishing: isFinishing || create.isPending,
  };
}
