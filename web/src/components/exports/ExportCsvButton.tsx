"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconDownload } from "@/components/icons";
import { Button, type ButtonVariant } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { CsvQuery, CsvTable } from "./csvExport";
import { useCsvExport } from "./useCsvExport";

/**
 * "Export CSV" for an owner (staff never see it: the API refuses them):
 * the table with the filters on screen. `iconOnly` keeps a narrow header
 * (the inbox's list column) to the icon, with the label for screen readers
 * and as the tooltip.
 */
export function ExportCsvButton({
  table,
  query,
  label,
  hint,
  iconOnly = false,
  variant = "secondary",
  disabled = false,
  className,
}: {
  table: CsvTable;
  query?: CsvQuery;
  /** The accessible name when it differs from "Export CSV". */
  label?: string;
  /** What the file holds, as the tooltip. */
  hint?: string;
  iconOnly?: boolean;
  variant?: ButtonVariant;
  disabled?: boolean;
  /** Size overrides (an icon-only button is 2rem square unless this sets its width). */
  className?: string;
}) {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const { exporting, download } = useCsvExport();

  if (!isOwner) {
    return null;
  }

  const text = t("dataExports.csv.button");
  return (
    <Button
      variant={variant}
      size="sm"
      isLoading={exporting === table}
      disabled={disabled}
      leadingIcon={<IconDownload className="size-4" aria-hidden />}
      aria-label={label ?? (iconOnly ? text : undefined)}
      title={hint ?? label}
      className={cn(iconOnly && "gap-0 px-0", className ?? (iconOnly ? "w-8" : undefined))}
      onClick={() => void download(table, query)}
    >
      {iconOnly ? null : text}
    </Button>
  );
}
