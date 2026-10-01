"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import type { ApiError } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { Alert, Checkbox, Fieldset, Spinner, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  applicableAutotestKinds,
  narrowedSelection,
  refusalReasons,
  type AssistantVersionDetails,
  type AutotestRunView,
  type AutotestScenarioKind,
  type Refusal,
} from "@/lib/assistant";
import { languageName } from "@/lib/format";

import { SCENARIO_KIND_LABELS } from "./AutotestsPanel";
import { RefusalReasons } from "./GoLiveChecklist";

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

interface RefusalState {
  reasons: Refusal[];
  error: ApiError;
}

/** A refused publish or rollback (409, or 403 for a forced publish), else null. */
function refusalOf(error: ApiError): RefusalState | null {
  return error.status === 409 || error.status === 403 ? { reasons: refusalReasons(error), error } : null;
}

/**
 * Publish a version (owner): a confirmation, and the API's refusal reasons
 * (by their codes: trial, agreement, profile, staff contact, autotests,
 * voice setup) with links to fix them.
 * `force` publishes a version that did not pass its autotests (platform admins).
 */
export function PublishDialog({
  version,
  liveNumber,
  force,
  onClose,
  onPublished,
  onRunAutotests,
  onRefused,
}: {
  version: AssistantVersionDetails;
  liveNumber: number | null;
  force: boolean;
  onClose: () => void;
  onPublished: (version: AssistantVersionDetails) => void;
  onRunAutotests: () => void;
  /** The API refused: what the page shows may be out of date. */
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [refusal, setRefusal] = useState<RefusalState | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);

  const publish = useApiMutation(
    (acceptFailedTests: boolean) =>
      api.POST("/v1/businesses/{business_id}/assistant-versions/{version_id}/publish", {
        params: { path: { business_id: business.id, version_id: version.id } },
        body: { accept_failed_tests: acceptFailedTests },
      }),
    { errorToast: false },
  );

  const submit = async () => {
    setRefusal(null);
    const result = await publish.run(force);
    if (result.ok) {
      toast.success(t("assistant.publish.done", { number: result.data.version_number }));
      onPublished(result.data);
      return;
    }
    const refused = refusalOf(result.error);
    if (refused) {
      setRefusal(refused);
      onRefused();
    } else {
      toast.error(result.error);
    }
  };

  return (
    <ConfirmDialog
      open
      variant={force ? "danger" : "primary"}
      title={force ? t("assistant.publish.forceTitle", { number: version.version_number }) : t("assistant.publish.title", { number: version.version_number })}
      description={
        liveNumber !== null
          ? t("assistant.publish.descriptionReplace", { live: liveNumber })
          : t("assistant.publish.descriptionFirst")
      }
      confirmLabel={force ? t("assistant.publish.forceConfirm") : t("assistant.publish.confirm")}
      pendingLabel={t("assistant.publish.publishing")}
      isPending={publish.isPending}
      confirmDisabled={force && !acknowledged}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {force ? (
        <>
          <Alert tone="danger" title={t("assistant.publish.forceWarningTitle")}>
            {t("assistant.publish.forceWarning")}
          </Alert>
          <Checkbox
            id="publish-acknowledge"
            label={t("assistant.publish.forceAcknowledge")}
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />
        </>
      ) : null}
      {refusal ? (
        <div role="alert" className="space-y-3 rounded-xl border border-danger/25 bg-danger-soft px-4 py-3">
          <p className="text-sm font-medium text-danger">{t("assistant.publish.refused")}</p>
          <RefusalReasons
            reasons={refusal.reasons}
            error={refusal.error}
            onRunAutotests={() => {
              onClose();
              onRunAutotests();
            }}
          />
        </div>
      ) : null}
    </ConfirmDialog>
  );
}

/** Make an earlier (archived) version live again. */
export function RollbackDialog({
  version,
  liveNumber,
  onClose,
  onRolledBack,
  onRefused,
}: {
  version: AssistantVersionDetails;
  liveNumber: number | null;
  onClose: () => void;
  onRolledBack: (version: AssistantVersionDetails) => void;
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [refusal, setRefusal] = useState<RefusalState | null>(null);

  const rollback = useApiMutation(
    () =>
      api.POST("/v1/businesses/{business_id}/assistant-versions/{version_id}/rollback", {
        params: { path: { business_id: business.id, version_id: version.id } },
      }),
    { errorToast: false },
  );

  const submit = async () => {
    setRefusal(null);
    const result = await rollback.run();
    if (result.ok) {
      toast.success(t("assistant.rollback.done", { number: result.data.version_number }));
      onRolledBack(result.data);
      return;
    }
    const refused = refusalOf(result.error);
    if (refused) {
      setRefusal(refused);
      onRefused();
    } else {
      toast.error(result.error);
    }
  };

  return (
    <ConfirmDialog
      open
      variant="danger"
      title={t("assistant.rollback.title", { number: version.version_number })}
      description={
        liveNumber !== null
          ? t("assistant.rollback.descriptionReplace", { live: liveNumber, number: version.version_number })
          : t("assistant.rollback.description", { number: version.version_number })
      }
      confirmLabel={t("assistant.rollback.confirm")}
      pendingLabel={t("assistant.rollback.rollingBack")}
      isPending={rollback.isPending}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {refusal ? (
        <div role="alert" className="space-y-3 rounded-xl border border-danger/25 bg-danger-soft px-4 py-3">
          <p className="text-sm font-medium text-danger">{t("assistant.rollback.refused")}</p>
          <RefusalReasons reasons={refusal.reasons} error={refusal.error} />
        </div>
      ) : null}
    </ConfirmDialog>
  );
}
