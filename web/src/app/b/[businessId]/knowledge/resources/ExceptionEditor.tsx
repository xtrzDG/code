"use client";

import { useId, useRef, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Field, Fieldset, Input, Modal, Radio, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  formatLocalDate,
  isLocalDate,
  specialHoursIntervals,
  type ResourceView,
  type ScheduleExceptionCreateBody,
  type ScheduleExceptionView,
  type TimeRangeRow,
} from "@/lib/resources";

const MAX_NOTE_LENGTH = 300;

/** Add a holiday, a closed day or a day with special hours (business-local date). */
export function ExceptionEditor({
  today,
  resources,
  onClose,
  onSaved,
}: {
  /** Today in the business time zone, "YYYY-MM-DD". */
  today: string;
  resources: readonly ResourceView[];
  onClose: () => void;
  onSaved: (exception: ScheduleExceptionView) => void;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const formId = useId();
  const rowSequence = useRef(1);

  const [date, setDate] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [isClosed, setClosed] = useState(true);
  const [rows, setRows] = useState<TimeRangeRow[]>([{ key: "row-0", opens: "10:00", closes: "16:00" }]);
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<{ date?: MessageKey; hours?: MessageKey }>({});

  const create = useMutation((body: ScheduleExceptionCreateBody) =>
    api.POST("/v1/businesses/{business_id}/schedule-exceptions", { params: { path: { business_id: business.id } }, body }),
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const found: { date?: MessageKey; hours?: MessageKey } = {};
    if (!isLocalDate(date)) {
      found.date = date === "" ? "validation.required" : "knowledge.exceptions.errors.date";
    } else if (date < today) {
      found.date = "knowledge.exceptions.errors.past";
    }
    const hours = !isClosed && isLocalDate(date) ? specialHoursIntervals(date, rows) : null;
    if (hours && !hours.ok) {
      found.hours = hours.error;
    }
    setErrors(found);
    if (found.date || found.hours) {
      return;
    }
    const result = await create.run({
      date,
      resource_id: resourceId === "" ? null : resourceId,
      is_closed_all_day: isClosed,
      special_hours: hours?.ok ? hours.intervals : [],
      note: note.trim() === "" ? null : note.trim(),
    });
    if (result.ok) {
      toast.success(t("knowledge.exceptions.added", { date: formatLocalDate(result.data.date, locale) }));
      onSaved(result.data);
    }
  };

  const updateRow = (key: string, patch: Partial<TimeRangeRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
    setErrors((current) => ({ ...current, hours: undefined }));
  };

  return (
    <Modal
      open
      onClose={() => {
        if (!create.isPending) {
          onClose();
        }
      }}
      size="lg"
      title={t("knowledge.exceptions.addTitle")}
      description={t("knowledge.exceptions.editorDescription", { timezone: format.timeZone })}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={create.isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={create.isPending} loadingText={t("common.saving")}>
            {t("knowledge.exceptions.add")}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("knowledge.exceptions.date")} error={errors.date && t(errors.date)} required>
            {(control) => (
              <Input
                {...control}
                type="date"
                min={today}
                value={date}
                autoFocus
                onChange={(event) => {
                  setDate(event.target.value);
                  setErrors((current) => ({ ...current, date: undefined }));
                }}
              />
            )}
          </Field>
          <Field label={t("knowledge.exceptions.appliesTo")}>
            {(control) => (
              <Select {...control} value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
                <option value="">{t("knowledge.exceptions.wholeBusiness")}</option>
                {resources.map((resource) => (
                  <option key={resource.id} value={resource.id}>
                    {resource.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>

        <Fieldset legend={t("knowledge.exceptions.kind")} error={errors.hours && t(errors.hours)}>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Radio
              id={`${formId}-closed`}
              name={`${formId}-kind`}
              label={t("knowledge.exceptions.closed")}
              checked={isClosed}
              onChange={() => setClosed(true)}
            />
            <Radio
              id={`${formId}-special`}
              name={`${formId}-kind`}
              label={t("knowledge.exceptions.specialHours")}
              checked={!isClosed}
              onChange={() => setClosed(false)}
            />
          </div>
          {!isClosed ? (
            <div className="space-y-2 rounded-xl border border-line p-3">
              {rows.map((row, index) => (
                <div key={row.key} className="flex flex-wrap items-center gap-2">
                  <Input
                    type="time"
                    className="w-32"
                    aria-label={`${t("knowledge.exceptions.opens")} ${index + 1}`}
                    aria-invalid={errors.hours ? true : undefined}
                    value={row.opens}
                    onChange={(event) => updateRow(row.key, { opens: event.target.value })}
                  />
                  <span className="text-ink-subtle" aria-hidden>
                    –
                  </span>
                  <Input
                    type="time"
                    className="w-32"
                    aria-label={`${t("knowledge.exceptions.closes")} ${index + 1}`}
                    aria-invalid={errors.hours ? true : undefined}
                    value={row.closes}
                    onChange={(event) => updateRow(row.key, { closes: event.target.value })}
                  />
                  {rows.length > 1 ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`${t("knowledge.exceptions.removeInterval")} ${index + 1}`}
                      title={t("knowledge.exceptions.removeInterval")}
                      onClick={() => setRows((current) => current.filter((item) => item.key !== row.key))}
                    >
                      <IconTrash className="size-4" aria-hidden />
                    </Button>
                  ) : null}
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                leadingIcon={<IconPlus className="size-4" aria-hidden />}
                onClick={() => {
                  rowSequence.current += 1;
                  setRows((current) => [...current, { key: `row-${rowSequence.current}`, opens: "", closes: "" }]);
                }}
              >
                {t("knowledge.exceptions.addInterval")}
              </Button>
              <p className="text-sm text-ink-muted">{t("knowledge.exceptions.hoursHint")}</p>
            </div>
          ) : null}
        </Fieldset>

        <Field label={t("knowledge.exceptions.note")} hint={t("knowledge.exceptions.noteHint")} optionalLabel={t("common.optional")}>
          {(control) => (
            <Input
              {...control}
              dir="auto"
              maxLength={MAX_NOTE_LENGTH}
              placeholder={t("knowledge.exceptions.notePlaceholder")}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
