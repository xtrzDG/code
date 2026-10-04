"use client";

import { useId } from "react";

import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Fieldset, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { SeasonsProblem } from "@/lib/knowledge/offerFields";
import { MAX_SEASONS, daysInMonth, monthNames, nextSeasonRow, type SeasonRow, type SeasonRowErrors } from "@/lib/knowledge/seasons";

/**
 * A room type's seasonal nightly rates: one row per season (name, first and
 * last day, rate per night), added and removed in place. Each bound is a
 * day and a month, every year.
 */
export function SeasonalRatesEditor({
  rows,
  currency,
  problem,
  onChange,
}: {
  rows: readonly SeasonRow[];
  currency: string;
  problem?: SeasonsProblem;
  onChange: (rows: SeasonRow[]) => void;
}) {
  const { t, locale } = useI18n();
  const months = monthNames(locale);
  const update = (key: string, patch: Partial<SeasonRow>) =>
    onChange(rows.map((row) => (row.key === key ? clampDays({ ...row, ...patch }) : row)));
  const overlap = problem?.overlap;

  return (
    <Fieldset legend={t("knowledge.offer.seasons")} hint={t("knowledge.offer.seasonsHint")}>
      {overlap ? (
        <p className="text-sm text-danger" role="alert">
          {t("knowledge.offer.errors.seasonOverlap", { first: overlap[0] + 1, second: overlap[1] + 1 })}
        </p>
      ) : null}
      {problem?.tooMany ? (
        <p className="text-sm text-danger" role="alert">
          {t("knowledge.offer.errors.tooManySeasons", { count: MAX_SEASONS })}
        </p>
      ) : null}
      {rows.length === 0 ? <p className="text-sm text-ink-subtle">{t("knowledge.offer.noSeasons")}</p> : null}
      <ol className="space-y-3">
        {rows.map((row, index) => (
          <SeasonRowFields
            key={row.key}
            row={row}
            number={index + 1}
            months={months}
            currency={currency}
            errors={problem?.rows[index]}
            isOverlapping={overlap ? overlap.includes(index) : false}
            onChange={(patch) => update(row.key, patch)}
            onRemove={() => onChange(rows.filter((other) => other.key !== row.key))}
          />
        ))}
      </ol>
      {rows.length < MAX_SEASONS ? (
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconPlus className="size-4" aria-hidden />}
          onClick={() => onChange([...rows, nextSeasonRow(rows)])}
        >
          {t("knowledge.offer.addSeason")}
        </Button>
      ) : null}
    </Fieldset>
  );
}

/** A day that the newly chosen month lacks moves to its last day (31 → 30 April). */
function clampDays(row: SeasonRow): SeasonRow {
  const startLast = daysInMonth(Number(row.startMonth));
  const endLast = daysInMonth(Number(row.endMonth));
  return {
    ...row,
    startDay: Number(row.startDay) > startLast ? String(startLast) : row.startDay,
    endDay: Number(row.endDay) > endLast ? String(endLast) : row.endDay,
  };
}

function SeasonRowFields({
  row,
  number,
  months,
  currency,
  errors,
  isOverlapping,
  onChange,
  onRemove,
}: {
  row: SeasonRow;
  number: number;
  months: readonly string[];
  currency: string;
  errors?: SeasonRowErrors;
  isOverlapping: boolean;
  onChange: (patch: Partial<SeasonRow>) => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const id = useId();
  const title = t("knowledge.offer.seasonTitle", { number });
  const bound = (which: "start" | "end") => {
    const month = which === "start" ? row.startMonth : row.endMonth;
    const day = which === "start" ? row.startDay : row.endDay;
    const label = t(which === "start" ? "knowledge.offer.from" : "knowledge.offer.to");
    return (
      <div role="group" aria-label={`${title}: ${label}`} className="space-y-1.5">
        <span className="block text-sm font-medium text-ink">{label}</span>
        <div className="flex gap-2">
          <Select
            aria-label={`${label}: ${t("knowledge.offer.day")}`}
            className="w-20 shrink-0"
            value={day}
            onChange={(event) => onChange(which === "start" ? { startDay: event.target.value } : { endDay: event.target.value })}
          >
            {Array.from({ length: daysInMonth(Number(month)) }, (_, index) => (
              <option key={index + 1} value={String(index + 1)}>
                {index + 1}
              </option>
            ))}
          </Select>
          <Select
            aria-label={`${label}: ${t("knowledge.offer.month")}`}
            className="min-w-0 flex-1"
            value={month}
            onChange={(event) => onChange(which === "start" ? { startMonth: event.target.value } : { endMonth: event.target.value })}
          >
            {months.map((name, index) => (
              <option key={name} value={String(index + 1)}>
                {name}
              </option>
            ))}
          </Select>
        </div>
      </div>
    );
  };

  return (
    <li
      aria-label={title}
      className={
        isOverlapping
          ? "rounded-xl border border-danger/50 bg-surface-muted/50 p-3 sm:p-4"
          : "rounded-xl border border-line bg-surface-muted/50 p-3 sm:p-4"
      }
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-ink">{title}</p>
        <Button
          variant="ghost"
          size="sm"
          aria-label={t("knowledge.offer.removeSeason", { number })}
          className="hover:text-danger"
          onClick={onRemove}
        >
          <IconTrash className="size-4" aria-hidden />
        </Button>
      </div>
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_10rem]">
        <div className="space-y-1.5">
          <label htmlFor={`${id}-name`} className="block text-sm font-medium text-ink">
            {t("knowledge.offer.seasonName")}
            <span className="ml-1.5 font-normal text-ink-subtle">({t("common.optional")})</span>
          </label>
          <Input
            id={`${id}-name`}
            dir="auto"
            maxLength={100}
            placeholder={t("knowledge.offer.seasonNamePlaceholder")}
            value={row.name}
            aria-invalid={errors?.name ? true : undefined}
            onChange={(event) => onChange({ name: event.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor={`${id}-rate`} className="block text-sm font-medium text-ink">
            {t("knowledge.offer.seasonRate", { currency })}
            <span className="ml-0.5 text-danger" aria-hidden>
              *
            </span>
          </label>
          <Input
            id={`${id}-rate`}
            inputMode="decimal"
            autoComplete="off"
            required
            value={row.rate}
            aria-invalid={errors?.rate ? true : undefined}
            aria-describedby={errors?.rate ? `${id}-rate-error` : undefined}
            onChange={(event) => onChange({ rate: event.target.value })}
          />
        </div>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {bound("start")}
        {bound("end")}
      </div>
      {[errors?.dates, errors?.name, errors?.rate].some(Boolean) ? (
        <ul className="mt-2 space-y-0.5 text-sm text-danger">
          {errors?.dates ? <li>{t(errors.dates)}</li> : null}
          {errors?.name ? <li>{t(errors.name)}</li> : null}
          {errors?.rate ? <li id={`${id}-rate-error`}>{t(errors.rate)}</li> : null}
        </ul>
      ) : null}
    </li>
  );
}
