"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus, IconUpload } from "@/components/icons";
import { Button, ButtonLink, Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { KnowledgeFilter, KnowledgeStatusFilter } from "@/lib/knowledge/kinds";
import { businessPath } from "@/lib/navigation";

import type { KnowledgeItemsState } from "../../_lib/useKnowledgeItems";
import { KIND_GROUP_LABELS } from "../hooks";

/** Kind and status filters, the menu import and "add an item". */
export function KnowledgeToolbar({ list }: { list: KnowledgeItemsState }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const { filter, setFilter, kinds } = list;
  const base = businessPath(business.id, "knowledge");
  return (
    <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
      <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
        <Field label={t("knowledge.items.kindFilter")} className="sm:w-56">
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
        <Field label={t("knowledge.items.statusFilter")} className="sm:w-56">
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
      </div>
      <div className="flex flex-wrap gap-2">
        <ButtonLink href={`${base}/import`} variant="secondary" leadingIcon={<IconUpload className="size-4" aria-hidden />}>
          {t("knowledge.items.import")}
        </ButtonLink>
        <Button
          leadingIcon={<IconPlus className="size-4" aria-hidden />}
          onClick={() => list.openEditor({ mode: "create", kind: list.defaultKind })}
        >
          {t("knowledge.items.add")}
        </Button>
      </div>
    </div>
  );
}
