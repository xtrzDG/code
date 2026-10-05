"use client";

/**
 * One conversation of the inbox, made for a phone first: the transcript
 * fills the screen under a folded header, what waits (a person needed, an
 * open request) sits above it, and the reply box with Resolve, Call and
 * Book stays at the bottom, so a notification's link leads straight to a
 * reply without scrolling. The customer's details and the team's notes
 * open in a panel (a column of their own on wide screens).
 */

import { useSearchParams } from "next/navigation";
import { useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { CustomerMessageModal } from "@/components/insights/CustomerMessageModal";
import { AnswerFixDialog } from "@/components/teaching/AnswerFixDialog";
import { CheckDialog } from "@/components/teaching/CheckDialog";
import { Card, ConfirmDialog, ErrorState, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";
import { checkFormFromRating, type CheckForm } from "@/lib/teachingChecks";

import { openHandoffOf, openRequestsOf } from "../../_lib/cardUpdates";
import { canReplyFromCard } from "../../_lib/conversationModel";
import { useRequestStatus, useResolveHandoff } from "../../_lib/useCardActions";
import { useConversationCard, useScrollToLatest } from "../../_lib/useConversationCard";
import { useMediaQuery, WIDE_PANEL_QUERY } from "../../_lib/useMediaQuery";
import { useNotes } from "../../_lib/useNotes";
import { useTeam } from "../../_lib/useTeam";
import { Composer } from "../composer/Composer";
import { ComposerActions } from "../composer/ComposerActions";
import { BookFromConversation } from "../details/BookFromConversation";
import { DetailsPanel } from "../details/DetailsPanel";
import { NotesPanel } from "../notes/NotesPanel";
import { AssignMenu } from "./AssignMenu";
import { ConversationDetailSkeleton } from "./ConversationDetailSkeleton";
import { ConversationPanel, type PanelTab } from "./ConversationPanel";
import { ConversationTopBar } from "./ConversationTopBar";
import { Transcript } from "./Transcript";
import { WorkStrip } from "./WorkStrip";

export function ConversationView({ conversationId }: { conversationId: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const searchParams = useSearchParams();
  const listQuery = searchParams.toString();
  const backHref = `${businessPath(business.id, "inbox")}${listQuery ? `?${listQuery}` : ""}`;
  const [draft, setDraft] = useState("");
  const [isBooking, setBooking] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [isResolveOpen, setResolveOpen] = useState(false);
  const [panel, setPanel] = useState<{ isOpen: boolean; tab: PanelTab }>({ isOpen: false, tab: "details" });
  const [openedAt] = useState(() => Date.now());
  const [fixing, setFixing] = useState<string | null>(null);
  const [check, setCheck] = useState<CheckForm | null>(null);
  const isWide = useMediaQuery(WIDE_PANEL_QUERY);
  const scrollArea = useRef<HTMLDivElement>(null);

  const { card, detail, earlier, addMessage } = useConversationCard(conversationId);
  const team = useTeam();
  const notes = useNotes(conversationId, card !== undefined);
  const resolve = useResolveHandoff(conversationId);
  const requests = useRequestStatus(conversationId);
  useScrollToLatest(scrollArea, conversationId, card?.messages?.length ?? 0);

  if (!card) {
    return detail.error ? (
      <Card>
        <ErrorState error={detail.error} onRetry={detail.reload} />
      </Card>
    ) : (
      <ConversationDetailSkeleton label={t("conversations.loadingOne")} />
    );
  }

  const { conversation } = card;
  const reply = card.reply ?? null;
  const openHandoff = openHandoffOf(card);
  const canBook = !conversation.is_sandbox;
  const noteItems = notes.notes.items;
  const noteCount = noteItems ? noteItems.length : null;
  const openPanel = (tab: PanelTab) => setPanel({ isOpen: true, tab });

  return (
    <article
      aria-labelledby="conversation-title"
      className={cn(
        "flex min-h-[calc(100dvh-3rem)] flex-col lg:grid lg:h-full lg:min-h-0 lg:gap-4",
        isWide ? "lg:grid-cols-[minmax(0,1fr)_22rem]" : "lg:grid-cols-1",
      )}
    >
      <div className="flex min-w-0 flex-1 flex-col lg:min-h-0">
        <ConversationTopBar
          businessId={business.id}
          conversation={conversation}
          backHref={backHref}
          assignMenu={
            card.assignment && !conversation.is_sandbox ? (
              <AssignMenu conversationId={conversationId} assignment={card.assignment} team={team} />
            ) : null
          }
          noteCount={noteCount}
          onNotes={() => openPanel("notes")}
          onDetails={() => openPanel("details")}
          showPanelButtons={!isWide}
        />
        <div
          ref={scrollArea}
          className="flex-1 space-y-5 py-4 lg:min-h-0 lg:overflow-y-auto lg:border-x lg:border-line lg:bg-surface lg:px-5 lg:py-5"
        >
          <WorkStrip
            handoff={openHandoff}
            requests={openRequestsOf(card)}
            isRequestPending={requests.isPending}
            onRequestStatus={(lead, status) => void requests.change(lead, status)}
          />
          <Transcript
            messages={card.messages ?? []}
            earlier={earlier}
            label={t("conversations.transcript")}
            onFixAnswer={isOwner ? setFixing : null}
          />
        </div>
        <Composer
          conversation={conversation}
          reply={reply}
          messages={card.messages ?? []}
          draft={draft}
          onDraft={setDraft}
          onSent={addMessage}
          onRefused={detail.reload}
          nowMs={openedAt}
          actions={
            <ComposerActions
              canResolve={openHandoff !== null}
              isResolving={resolve.isPending}
              phone={conversation.contact_phone_number ?? null}
              canBook={canBook}
              onResolve={() => setResolveOpen(true)}
              onBook={() => setBooking(true)}
            />
          }
        />
      </div>

      <ConversationPanel
        tab={panel.tab}
        onTab={(tab) => setPanel((current) => ({ ...current, tab }))}
        isOpen={panel.isOpen}
        onClose={() => setPanel((current) => ({ ...current, isOpen: false }))}
        isInline={isWide}
        noteCount={noteCount}
        details={
          <DetailsPanel
            detail={card}
            onBook={canBook ? () => setBooking(true) : null}
            onFixAnswer={isOwner ? setFixing : null}
            onSaveCheck={
              isOwner
                ? (answerId) =>
                    setCheck(checkFormFromRating(card.messages ?? [], conversation, answerId, business.default_language))
                : null
            }
          />
        }
        notes={<NotesPanel notes={notes} />}
      />

      <ConfirmDialog
        open={isResolveOpen}
        tone="primary"
        title={t("inboxCard.resolveConfirm.title")}
        description={t("inboxCard.resolveConfirm.description", {
          name: conversation.contact_name ?? t("insights.unknownCustomer"),
        })}
        confirmLabel={t("inboxCard.resolveConfirm.confirm")}
        onClose={() => setResolveOpen(false)}
        onConfirm={() => {
          setResolveOpen(false);
          if (openHandoff) {
            void resolve.resolve(openHandoff);
          }
        }}
      />

      <BookFromConversation
        open={isBooking}
        conversation={conversation}
        onClose={() => setBooking(false)}
        onCreated={(result) => {
          setBooking(false);
          detail.reload();
          toast.success(t("bookings.created"));
          // The reply box takes it freely or, past WhatsApp's 24 hours, in
          // the owner's template; otherwise staff copy it by hand.
          if (canReplyFromCard(reply)) {
            setDraft(result.confirmation_text);
            toast.info(t("conversations.reply.confirmationPrefilled"));
          } else {
            setConfirmation(result.confirmation_text);
          }
        }}
      />

      <AnswerFixDialog conversationId={conversationId} messageId={fixing} onClose={() => setFixing(null)} />
      {check ? (
        <CheckDialog
          open
          initial={check}
          check={null}
          title={t("teaching.checks.saveTitle")}
          description={t("teaching.checks.saveDescription")}
          onClose={() => setCheck(null)}
        />
      ) : null}

      <CustomerMessageModal
        open={confirmation !== null}
        title={t("bookings.created")}
        text={confirmation ?? ""}
        onClose={() => setConfirmation(null)}
      />
    </article>
  );
}
