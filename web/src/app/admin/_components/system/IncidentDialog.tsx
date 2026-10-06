"use client";

import { useState, type FormEvent } from "react";

import { Button, DateTimeField, Field, Input, Modal, Select, Textarea } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";

import {
  INCIDENT_KINDS,
  INCIDENT_SEVERITIES,
  TITLE_MAX_LENGTH,
  buildIncidentBody,
  emptyIncidentForm,
  withKind,
  type CreateIncidentBody,
  type Incident,
  type IncidentForm,
  type IncidentFormErrors,
  type IncidentKind,
  type IncidentProblem,
  type IncidentSeverity,
} from "../../_lib/incidentForm";
import { BreachNoticeFields } from "./BreachNoticeFields";

const NO_ERRORS: IncidentFormErrors = { fields: {}, notices: {}, unknownBusinesses: [] };

interface IncidentDialogProps {
  open: boolean;
  onClose: () => void;
  onRecord: (body: CreateIncidentBody) => Promise<Incident | null>;
  isRecording: boolean;
  error: unknown;
}

/** "Record incident": the form is new each time it opens. */
export function IncidentDialog({ open, onClose, ...form }: IncidentDialogProps) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} size="lg" title={t("adminIncident.title")} description={t("adminIncident.description")}>
      {open ? <IncidentFormBody onClose={onClose} {...form} /> : null}
    </Modal>
  );
}

function IncidentFormBody({ onClose, onRecord, isRecording, error }: Omit<IncidentDialogProps, "open">) {
  const { t } = useI18n();
  const [form, setForm] = useState<IncidentForm>(() => emptyIncidentForm(Date.now() * 1000));
  const [errors, setErrors] = useState<IncidentFormErrors>(NO_ERRORS);
  const isBreach = form.kind === "data_breach";

  const update = (patch: Partial<IncidentForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors(NO_ERRORS);
  };

  const errorText = (problem: IncidentProblem) =>
    t(`adminIncident.errors.${problem}`, { tokens: errors.unknownBusinesses.slice(0, 3).join(", ") });

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildIncidentBody(form, Date.now() * 1000);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    if (await onRecord(built.body)) {
      onClose();
    }
  };

  const fieldError = (field: keyof IncidentFormErrors["fields"]) => {
    const problem = errors.fields[field];
    return problem ? errorText(problem) : undefined;
  };
  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("adminIncident.kind")} required>
          {(control) => (
            <Select {...control} value={form.kind} onChange={(event) => update(withKind(form, event.target.value as IncidentKind))}>
              {INCIDENT_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`adminSystem.incidents.kinds.${kind}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={t("adminIncident.severity")}
          required
          hint={isBreach ? t("adminIncident.severityBreach") : undefined}
        >
          {(control) => (
            <Select
              {...control}
              value={isBreach ? "sev1" : form.severity}
              disabled={isBreach}
              onChange={(event) => update({ severity: event.target.value as IncidentSeverity })}
            >
              {INCIDENT_SEVERITIES.map((severity) => (
                <option key={severity} value={severity}>
                  {t(`adminSystem.severity.${severity}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      {!isBreach ? <p className="-mt-2 text-xs text-ink-muted">{t("adminIncident.severityHint")}</p> : null}

      <Field label={t("adminIncident.name")} hint={t("adminIncident.nameHint")} required error={fieldError("title")}>
        {(control) => (
          <Input
            {...control}
            dir="auto"
            autoComplete="off"
            maxLength={TITLE_MAX_LENGTH}
            value={form.title}
            onChange={(event) => update({ title: event.target.value })}
          />
        )}
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("adminIncident.startedAt")} required error={fieldError("startedAt")}>
          {(control) => (
            <DateTimeField {...control} value={form.startedAt} onChange={(startedAt) => update({ startedAt })} />
          )}
        </Field>
        <Field label={t("adminIncident.detectedAt")} optionalLabel={t("common.optional")} error={fieldError("detectedAt")}>
          {(control) => (
            <DateTimeField {...control} value={form.detectedAt} onChange={(detectedAt) => update({ detectedAt })} />
          )}
        </Field>
      </div>
      <p className="-mt-2 text-xs text-ink-muted">
        {t("adminIncident.detectedHint")} {t("adminIncident.timeZone")}
      </p>

      <Field label={t("adminIncident.businesses")} hint={t("adminIncident.businessesHint")} required error={fieldError("businesses")}>
        {(control) => (
          <Textarea
            {...control}
            dir="ltr"
            rows={3}
            spellCheck={false}
            className="font-mono text-xs"
            value={form.businesses}
            onChange={(event) => update({ businesses: event.target.value })}
          />
        )}
      </Field>

      {isBreach ? <BreachNoticeFields form={form} errors={errors} errorText={errorText} onChange={update} /> : null}

      <InlineError error={error} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={isRecording}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" variant={isBreach ? "danger" : "primary"} isLoading={isRecording} loadingText={t("adminIncident.saving")}>
          {t(isBreach ? "adminIncident.submitBreach" : "adminIncident.submit")}
        </Button>
      </div>
    </form>
  );
}
