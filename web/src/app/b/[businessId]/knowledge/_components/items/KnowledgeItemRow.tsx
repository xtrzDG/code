"use client";

import type { KnowledgeItemDetails } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconPencil, IconTrash } from "@/components/icons";
import { Switch } from "@/components/content/Switch";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

/** One item: title, draft or off badges, price, duration and languages; switch, edit and delete. */
export function KnowledgeItemRow({
  item,
  onToggle,
  onEdit,
  onDelete,
}: {
  item: KnowledgeItemDetails;
  onToggle: (isActive: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const meta = [
    item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor) : null,
    item.duration_minutes ? t("knowledge.items.minutes", { count: item.duration_minutes }) : null,
    (item.languages ?? []).length > 0 ? (item.languages ?? []).map((language) => languageName(language, locale)).join(", ") : null,
  ].filter((part): part is string => part !== null);

  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium break-words text-ink" dir="auto">
            {item.title}
          </p>
          {!item.is_active ? (
            <Badge tone={item.source === "menu_import" ? "warning" : "neutral"}>
              {item.source === "menu_import" ? t("knowledge.items.importDraft") : t("knowledge.items.off")}
            </Badge>
          ) : null}
          {item.source === "unanswered_question" ? <Badge tone="info">{t("knowledge.items.fromQuestion")}</Badge> : null}
        </div>
        {item.body ? (
          <p className="mt-1 line-clamp-2 text-sm break-words whitespace-pre-line text-ink-muted" dir="auto">
            {item.body}
          </p>
        ) : null}
        {meta.length > 0 ? <p className="mt-1.5 text-sm text-ink-subtle">{meta.join(" · ")}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:pt-0.5">
        <span className="mr-2 flex items-center gap-2 text-sm text-ink-muted">
          <Switch
            checked={item.is_active}
            label={t("knowledge.items.useToggle", { title: item.title })}
            onChange={onToggle}
          />
          <span aria-hidden className="sm:hidden">
            {item.is_active ? t("knowledge.items.used") : t("knowledge.items.notUsed")}
          </span>
        </span>
        <Button
          variant="ghost"
          size="sm"
          leadingIcon={<IconPencil className="size-4" aria-hidden />}
          aria-label={`${t("common.edit")}: ${item.title}`}
          onClick={onEdit}
        >
          {t("common.edit")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`${t("common.delete")}: ${item.title}`}
          title={t("common.delete")}
          className="hover:text-danger"
          onClick={onDelete}
        >
          <IconTrash className="size-4" aria-hidden />
        </Button>
      </div>
    </li>
  );
}
