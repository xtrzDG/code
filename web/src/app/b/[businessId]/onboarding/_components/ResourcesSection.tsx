"use client";

import { useState, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { ResourceKind } from "@/api/types";
import { IconPlus } from "@/components/icons";
import { Badge, Button, Field, Input, LoadingRegion, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { StepSection } from "./StepForm";

const MAX_COUNT = 10_000;

function positiveInteger(text: string, max: number): number | null {
  const trimmed = text.trim();
  return /^\d+$/.test(trimmed) && Number(trimmed) >= 1 && Number(trimmed) <= max ? Number(trimmed) : null;
}

/**
 * Bookable resources (tables, rooms, arenas, masters): listed and added
 * right away with POST …/resources, apart from the step's own save.
 */
export function ResourcesSection({
  businessId,
  resourceKind,
  resourceNoun,
  canEdit,
  onChanged,
}: {
  businessId: string;
  resourceKind: ResourceKind;
  resourceNoun: string;
  canEdit: boolean;
  /** Called after a resource was added (the "what to add" list changes). */
  onChanged: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const resources = useQuery(queryKeys.resources.list(businessId), () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } } }),
  );
  const create = useMutation(
    (body: { name: string; capacity: number; unit_count: number; kind: ResourceKind }) =>
      api.POST("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } }, body }),
    { invalidate: [queryKeys.resources.all(businessId)], stale: [queryKeys.assistant.all(businessId)] },
  );

  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("");
  const [units, setUnits] = useState("1");
  const [errors, setErrors] = useState<{ name?: MessageKey; capacity?: MessageKey; units?: MessageKey }>({});

  const add = async () => {
    const parsedCapacity = positiveInteger(capacity, MAX_COUNT);
    const parsedUnits = positiveInteger(units || "1", 1000);
    const found = {
      ...(name.trim() === "" ? { name: "validation.required" as const } : {}),
      ...(parsedCapacity === null ? { capacity: "validation.positive" as const } : {}),
      ...(parsedUnits === null ? { units: "validation.positive" as const } : {}),
    };
    setErrors(found);
    if (parsedCapacity === null || parsedUnits === null || found.name) {
      return;
    }
    const result = await create.run({ name: name.trim(), capacity: parsedCapacity, unit_count: parsedUnits, kind: resourceKind });
    if (result.ok) {
      toast.success(t("onboarding.resources.added"));
      setName("");
      setCapacity("");
      setUnits("1");
      onChanged();
    }
  };

  // Enter adds the resource instead of submitting the whole step.
  const addOnEnter = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void add();
    }
  };

  const items = resources.data?.items ?? [];

  return (
    <StepSection title={t("onboarding.resources.title")} hint={t("onboarding.resources.hint", { noun: resourceNoun })}>
      {resources.isLoading && !resources.data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonRows rows={2} />
        </LoadingRegion>
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("onboarding.resources.empty")}</p>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line">
          {items.map((resource) => (
            <li key={resource.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
              <span className="font-medium text-ink">{resource.name}</span>
              <span className="text-ink-muted">
                {t("onboarding.resources.capacity")}: {resource.capacity}
              </span>
              {resource.unit_count > 1 ? (
                <span className="text-ink-muted">
                  {t("onboarding.resources.units")}: {resource.unit_count}
                </span>
              ) : null}
              {!resource.is_active ? <Badge>{t("onboarding.resources.inactive")}</Badge> : null}
            </li>
          ))}
        </ul>
      )}

      {canEdit ? (
        <div className="grid gap-4 rounded-xl bg-surface-muted/50 p-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-start">
          <Field label={t("onboarding.resources.name")} error={errors.name && t(errors.name)}>
            {(control) => (
              <Input
                {...control}
                value={name}
                maxLength={200}
                placeholder={t("onboarding.resources.namePlaceholder")}
                onKeyDown={addOnEnter}
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </Field>
          <Field label={t("onboarding.resources.capacity")} error={errors.capacity && t(errors.capacity)}>
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                value={capacity}
                onKeyDown={addOnEnter}
                onChange={(event) => setCapacity(event.target.value)}
              />
            )}
          </Field>
          <Field label={t("onboarding.resources.units")} error={errors.units && t(errors.units)}>
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                value={units}
                onKeyDown={addOnEnter}
                onChange={(event) => setUnits(event.target.value)}
              />
            )}
          </Field>
          <Button
            variant="secondary"
            className="sm:mt-7"
            leadingIcon={<IconPlus className="size-4" aria-hidden />}
            isLoading={create.isPending}
            onClick={() => void add()}
          >
            {t("onboarding.resources.add")}
          </Button>
        </div>
      ) : null}
    </StepSection>
  );
}
