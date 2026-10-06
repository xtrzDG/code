"use client";

import { IconPencil } from "@/components/icons";
import { Switch } from "@/components/content/Switch";
import { Badge, Button, UserSentence } from "@/components/ui";
import type { KnowledgeItemDetails } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";
import { servicesOf } from "@/lib/offers";
import type { ResourceView } from "@/lib/resources";

import { BOOKING_UNIT_LABELS, RESOURCE_KIND_LABELS } from "../ResourceEditor";

/**
 * One bookable resource: name, kind, capacity, units, slot and hours, the
 * services it performs or its room type; switch and edit.
 */
export function ResourceRow({
  resource,
  offers,
  onToggle,
  onEdit,
}: {
  resource: ResourceView;
  offers: readonly KnowledgeItemDetails[];
  onToggle: (isActive: boolean) => void;
  onEdit: () => void;
}) {
  const { t, tp, locale } = useI18n();
  const services = servicesOf(resource, offers).map((item) => item.title);
  const roomType = resource.room_type_item_id ? offers.find((item) => item.id === resource.room_type_item_id) : undefined;
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
          <p className={resource.is_active ? "font-medium text-ink" : "font-medium text-ink-muted"} dir="auto" data-user-content>
            {resource.name}
          </p>
          {!resource.is_active ? <Badge>{t("knowledge.resources.inactive")}</Badge> : null}
        </div>
        <p className="text-sm text-ink-subtle">{details.join(" · ")}</p>
        <p className="text-sm text-ink-subtle">
          {ownHours.length > 0 ? t("knowledge.resources.ownHoursSet") : t("knowledge.resources.followsBusiness")}
        </p>
        {services.length > 0 ? (
          <p className="line-clamp-2 text-sm text-ink-muted">
            <UserSentence
              text={t("knowledge.resources.servesValue")}
              values={{ names: listFormat(locale, { type: "conjunction" }).format(services) }}
            />
          </p>
        ) : null}
        {roomType ? (
          <p className="text-sm text-ink-muted">
            <UserSentence text={t("knowledge.resources.roomTypeValue")} values={{ name: roomType.title }} />
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <span className="mr-2 flex items-center gap-2">
          <Switch
            checked={resource.is_active}
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
