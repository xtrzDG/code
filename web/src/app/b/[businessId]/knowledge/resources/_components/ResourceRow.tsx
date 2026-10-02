"use client";

import { IconPencil } from "@/components/icons";
import { Switch } from "@/components/content/Switch";
import { Badge, Button, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ResourceView } from "@/lib/resources";

import { BOOKING_UNIT_LABELS, RESOURCE_KIND_LABELS } from "../ResourceEditor";

/** One bookable resource: name, kind, capacity, units, slot and hours; switch and edit. */
export function ResourceRow({
  resource,
  isToggling,
  onToggle,
  onEdit,
}: {
  resource: ResourceView;
  isToggling: boolean;
  onToggle: (isActive: boolean) => void;
  onEdit: () => void;
}) {
  const { t, tp } = useI18n();
  const details = [
    t(RESOURCE_KIND_LABELS[resource.kind]),
    tp("knowledge.resources.capacityValue", resource.capacity),
    resource.unit_count > 1 ? t("knowledge.resources.unitsValue", { count: resource.unit_count }) : null,
    resource.slot_minutes ? t("knowledge.resources.slotValue", { count: resource.slot_minutes }) : null,
    resource.booking_unit === "night" ? t(BOOKING_UNIT_LABELS.night) : null,
  ].filter((part): part is string => part !== null);
  const ownHours = resource.schedule ?? [];
  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={resource.is_active ? "font-medium text-ink" : "font-medium text-ink-muted"} dir="auto">
            {resource.name}
          </p>
          {!resource.is_active ? <Badge>{t("knowledge.resources.inactive")}</Badge> : null}
        </div>
        <p className="text-sm text-ink-subtle">{details.join(" · ")}</p>
        <p className="text-sm text-ink-subtle">
          {ownHours.length > 0 ? t("knowledge.resources.ownHoursSet") : t("knowledge.resources.followsBusiness")}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <span className="mr-2 flex items-center gap-2">
          {isToggling ? <Spinner size="sm" /> : null}
          <Switch
            checked={resource.is_active}
            disabled={isToggling}
            label={t("knowledge.resources.toggle", { name: resource.name })}
            onChange={onToggle}
          />
        </span>
        <Button
          variant="ghost"
          size="sm"
          leadingIcon={<IconPencil className="size-4" aria-hidden />}
          aria-label={`${t("common.edit")}: ${resource.name}`}
          onClick={onEdit}
        >
          {t("common.edit")}
        </Button>
      </div>
    </li>
  );
}
