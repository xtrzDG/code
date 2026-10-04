"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus, IconUpload } from "@/components/icons";
import { Button, ButtonLink, Field, FilterSheet, Select, usePageLevel, usePhoneChrome, usePhoneFab } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { KnowledgeFilter, KnowledgeStatusFilter } from "@/lib/knowledge/kinds";
import { businessPath } from "@/lib/navigation";

import type { KnowledgeItemsState } from "../../_lib/useKnowledgeItems";
import { KIND_GROUP_LABELS } from "../hooks";

function FilterFields({ list, layout }: { list: KnowledgeItemsState; layout: "row" | "sheet" }) {
  const { t } = useI18n();
  const { filter, setFilter, kinds } = list;
  const width = layout === "row" ? "sm:w-56" : undefined;
  return (
    <>
      <Field label={t("knowledge.items.kindFilter")} className={width}>
        {(control) => (
          <Select
            {...control}
            value={filter.kind}
            onChange={(event) => setFilter((current) => ({ ...current, kind: event.target.value as KnowledgeFilter["kind"] }))}
          >
            <option value="all">{t("knowledge.items.allKinds")}</option>
            {kinds.map((kind) => (
              <option key={kind} value={kind}>
                {t(KIND_GROUP_LABELS[kind])}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("knowledge.items.statusFilter")} className={width}>
        {(control) => (
          <Select
            {...control}
            value={filter.status}
            onChange={(event) => setFilter((current) => ({ ...current, status: event.target.value as KnowledgeStatusFilter }))}
          >
            <option value="all">{t("knowledge.items.statusAll")}</option>
            <option value="active">{t("knowledge.items.statusActive")}</option>
            <option value="inactive">{t("knowledge.items.statusInactive")}</option>
          </Select>
        )}
      </Field>
    </>
  );
}

/**
 * Kind and status filters, the menu import and "add an item". On phones
 * the filters fold behind "Filters" and "Add an item" becomes the floating
 * button above the tab bar.
 */
export function KnowledgeToolbar({ list }: { list: KnowledgeItemsState }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const hasFab = usePhoneChrome()?.hasFabSlot ?? false;
  const base = businessPath(business.id, "assistant/knowledge");
  const addItem = () => list.openEditor({ mode: "create", kind: list.defaultKind });
  usePhoneFab(usePageLevel(), { label: t("knowledge.items.add"), icon: IconPlus, onClick: addItem, opensDialog: true });
  const activeCount = [list.filter.kind !== "all", list.filter.status !== "all"].filter(Boolean).length;
  const importLink = (
    <ButtonLink href={`${base}/import`} variant="secondary" className="max-lg:h-10" leadingIcon={<IconUpload className="size-4" aria-hidden />}>
      {t("knowledge.items.import")}
    </ButtonLink>
  );

  return (
    <div className="border-b border-line px-4 py-4 sm:px-6">
      <FilterSheet
        activeCount={activeCount}
        onClear={() => list.setFilter({ kind: "all", status: "all" })}
        trailing={
          <>
            {importLink}
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={addItem} className={cn("h-10", hasFab && "hidden")}>
              {t("knowledge.items.add")}
            </Button>
          </>
        }
        inline={
          <div className="flex flex-row items-end justify-between gap-3">
            <div className="flex flex-wrap gap-3">
              <FilterFields list={list} layout="row" />
            </div>
            <div className="flex flex-wrap gap-2">
              {importLink}
              <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={addItem}>
                {t("knowledge.items.add")}
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          <FilterFields list={list} layout="sheet" />
        </div>
      </FilterSheet>
    </div>
  );
}
