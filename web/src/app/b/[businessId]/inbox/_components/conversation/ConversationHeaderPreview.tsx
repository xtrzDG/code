"use client";

/**
 * The header of a conversation on its way, drawn from what the inbox list
 * already knows (the customer's name or number): it shows at once, in the
 * same place as the real header (ConversationTopBar), and the opened row's
 * customer flies into it (SharedMorph), so the person sees where they went
 * before the card arrives. Nothing when the list does not know the
 * conversation (opened from a notification's link).
 */

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconArrowLeft } from "@/components/icons";
import { morphName, SharedMorph } from "@/components/motion/SharedMorph";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";
import { formatPhone } from "@/lib/phone";

import { initialsOf } from "../../_lib/conversationModel";
import { useRowPreview } from "../list/RowSourceContext";

export function ConversationHeaderPreview({ conversationId }: { conversationId?: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const params = useParams<{ conversationId?: string }>();
  const listQuery = useSearchParams().toString();
  const id = conversationId ?? params.conversationId ?? null;
  const preview = useRowPreview(id);
  if (!preview) {
    return null;
  }
  const name = preview.contactName ?? (preview.contactPhone ? formatPhone(preview.contactPhone) : t("insights.unknownCustomer"));
  const backHref = `${businessPath(business.id, "inbox")}${listQuery ? `?${listQuery}` : ""}`;

  return (
    <div
      data-conversation-preview=""
      className={cn(
        "sticky top-0 z-20 -mx-4 -mt-6 flex items-center gap-2 border-b border-line bg-canvas/85 px-3 pt-[calc(0.5rem+env(safe-area-inset-top))] pb-2 backdrop-blur-xl sm:-mx-6 sm:px-5",
        "lg:static lg:mx-0 lg:mt-0 lg:rounded-2xl lg:border lg:bg-surface lg:px-4 lg:py-3 lg:backdrop-blur-none",
      )}
    >
      <Link
        href={backHref}
        aria-label={t("inboxCard.back")}
        className="flex size-10 shrink-0 items-center justify-center rounded-full text-ink-muted hover:text-ink lg:hidden"
      >
        <IconArrowLeft className="size-5 rtl:-scale-x-100" aria-hidden />
      </Link>
      <SharedMorph name={morphName("conversation-avatar", preview.id)}>
        <span
          aria-hidden
          data-user-content
          className="hidden size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink sm:flex"
        >
          {initialsOf(preview.contactName)}
        </span>
      </SharedMorph>
      <div className="min-w-0 flex-1 py-2.5 leading-tight">
        <SharedMorph name={morphName("conversation-name", preview.id)}>
          <p className="truncate text-start text-base font-semibold text-ink">
            <bdi dir={preview.contactName ? "auto" : "ltr"} data-user-content={preview.contactName ? true : undefined}>
              {name}
            </bdi>
          </p>
        </SharedMorph>
      </div>
    </div>
  );
}
