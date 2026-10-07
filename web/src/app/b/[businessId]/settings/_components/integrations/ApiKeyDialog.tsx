"use client";

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { Alert, Button, Checkbox, Field, Fieldset, Input, Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { scopeLabelKey, type ApiKeyScope, type CreatedApiKey } from "@/lib/apiIntegrations";

import { API_KEY_REASONS, type useApiKeys } from "../../_lib/useApiKeys";

/** Creates an API key: what it is for and what it may do. Its token goes to `onCreated`. */
export function ApiKeyDialog({
  open,
  scopes,
  apiKeys,
  onClose,
  onCreated,
}: {
  open: boolean;
  scopes: readonly ApiKeyScope[];
  apiKeys: ReturnType<typeof useApiKeys>;
  onClose: () => void;
  onCreated: (created: CreatedApiKey) => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [chosen, setChosen] = useState<ApiKeyScope[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [scopesMissing, setScopesMissing] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (chosen.length === 0) {
      setScopesMissing(true);
      return;
    }
    setError(null);
    const result = await apiKeys.createKey({ name: name.trim(), scopes: scopes.filter((scope) => chosen.includes(scope)) });
    if (result.ok) onCreated(result.data);
    else setError(result.error);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("apiIntegrations.apiKeys.dialog.title")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form="api-key-new" isLoading={apiKeys.isCreating}>
            {t("apiIntegrations.apiKeys.dialog.create")}
          </Button>
        </>
      }
    >
      <form id="api-key-new" onSubmit={submit} className="space-y-5" noValidate>
        {error ? <Alert tone="danger">{describeError(error, t, undefined, API_KEY_REASONS).title}</Alert> : null}
        <Field label={t("apiIntegrations.apiKeys.dialog.name")} hint={t("apiIntegrations.apiKeys.dialog.nameHint")} required>
          {(control) => <Input {...control} maxLength={80} autoComplete="off" value={name} onChange={(event) => setName(event.target.value)} />}
        </Field>
        <Fieldset
          legend={t("apiIntegrations.apiKeys.dialog.scopes")}
          hint={t("apiIntegrations.apiKeys.dialog.scopesHint")}
          error={scopesMissing ? t("apiIntegrations.apiKeys.dialog.scopesMissing") : undefined}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {scopes.map((scope) => (
              <Checkbox
                key={scope}
                label={t(scopeLabelKey(scope))}
                description={<code dir="ltr" className="font-mono text-xs">{scope}</code>}
                checked={chosen.includes(scope)}
                onChange={(event) => {
                  setScopesMissing(false);
                  const checked = event.target.checked;
                  setChosen((current) => (checked ? [...current, scope] : current.filter((item) => item !== scope)));
                }}
              />
            ))}
          </div>
        </Fieldset>
      </form>
    </Modal>
  );
}
