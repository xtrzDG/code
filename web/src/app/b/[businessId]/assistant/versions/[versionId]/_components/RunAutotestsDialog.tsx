"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { Alert, Checkbox, Fieldset, Spinner, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  applicableAutotestKinds,
  narrowedSelection,
  type AutotestRunView,
  type AutotestScenarioKind,
} from "@/lib/assistant/autotests";
import type { AssistantVersionDetails } from "@/lib/assistant/versions";
import { languageName } from "@/lib/format";

import { SCENARIO_KIND_LABELS } from "../_lib/scenarioLabels";

/** Start the autotests, in every language and scenario or a narrowed selection. */
export function RunAutotestsDialog({
  version,
  onClose,
  onStarted,
}: {
  version: AssistantVersionDetails;
  onClose: () => void;
  onStarted: (run: AutotestRunView) => void;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const niche = useApiQuery(
    () =>
      api.GET("/v1/catalog/niches/{niche_key}", {
        params: { path: { niche_key: version.niche_key }, query: { language: locale } },
      }),
    [version.niche_key, locale],
  );
  const kinds = applicableAutotestKinds(niche.data?.autotest_kinds ?? [], version.tools);
  const [languages, setLanguages] = useState<string[]>(version.languages);
  const [excludedKinds, setExcludedKinds] = useState<ReadonlySet<AutotestScenarioKind>>(new Set());

  const start = useApiMutation((body: { languages: string[] | null; kinds: AutotestScenarioKind[] | null }) =>
    api.POST("/v1/businesses/{business_id}/assistant-versions/{version_id}/autotests", {
      params: { path: { business_id: business.id, version_id: version.id } },
      body,
    }),
  );

  const chosenKinds = kinds.filter((kind) => !excludedKinds.has(kind));
  const languageSelection = narrowedSelection(languages, version.languages);
  const kindSelection = niche.data ? narrowedSelection(chosenKinds, kinds) : null;
  const isNarrowed = languageSelection !== null || kindSelection !== null;
  const isEmpty = languages.length === 0 || (niche.data !== undefined && chosenKinds.length === 0);

  const submit = async () => {
    const result = await start.run({ languages: languageSelection, kinds: kindSelection });
    if (result.ok) {
      toast.success(t("assistant.autotests.started"));
      onStarted(result.data);
    }
  };

  return (
    <ConfirmDialog
      open
      variant="primary"
      title={t("assistant.autotests.runTitle", { number: version.version_number })}
      description={t("assistant.autotests.runDescription")}
      confirmLabel={t("assistant.autotests.run")}
      pendingLabel={t("assistant.autotests.starting")}
      isPending={start.isPending}
      confirmDisabled={isEmpty}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {version.languages.length > 1 ? (
        <Fieldset legend={t("assistant.autotests.languages")}>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {version.languages.map((language) => (
              <Checkbox
                key={language}
                id={`autotest-language-${language}`}
                label={languageName(language, locale)}
                checked={languages.includes(language)}
                onChange={(event) =>
                  setLanguages((current) => (event.target.checked ? [...current, language] : current.filter((item) => item !== language)))
                }
              />
            ))}
          </div>
        </Fieldset>
      ) : null}
      <Fieldset legend={t("assistant.autotests.scenarios")}>
        {niche.isLoading && !niche.data ? (
          <Spinner size="sm" label={t("common.loading")} />
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {kinds.map((kind) => (
              <Checkbox
                key={kind}
                id={`autotest-kind-${kind}`}
                label={t(SCENARIO_KIND_LABELS[kind])}
                checked={!excludedKinds.has(kind)}
                onChange={(event) =>
                  setExcludedKinds((current) => {
                    const next = new Set(current);
                    if (event.target.checked) {
                      next.delete(kind);
                    } else {
                      next.add(kind);
                    }
                    return next;
                  })
                }
              />
            ))}
          </div>
        )}
      </Fieldset>
      {isNarrowed ? <Alert tone="info">{t("assistant.autotests.narrowedHint")}</Alert> : null}
    </ConfirmDialog>
  );
}
