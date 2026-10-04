"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconBell, IconPlus } from "@/components/icons";
import { Button, ButtonLink, Card, EmptyState, Modal } from "@/components/ui";
import { ConfirmDialog } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { MAX_MANAGER_CONTACTS, type ManagerContact } from "../_lib/contacts";
import { languageChoices } from "../_lib/general";
import { useManagerContacts } from "../_lib/useManagerContacts";
import { useMyNotifications } from "../_lib/useMyNotifications";
import { useNotificationContacts } from "../_lib/useNotificationContacts";
import { ContactFormView } from "./notifications/ContactFormView";
import { ContactRow } from "./notifications/ContactRow";
import { STALE_LIST_MESSAGES } from "./notifications/contactTexts";
import { MyEventsCard } from "./notifications/MyEventsCard";
import { SetupRemindersCard } from "./notifications/SetupRemindersCard";
import { ThisDeviceCard } from "./notifications/ThisDeviceCard";

/**
 * Settings → Notifications, for every member: this device (Web Push), the
 * events and quiet hours of my devices, the setup reminders (owners), and
 * the staff contacts with how notifications reach each one (owners add,
 * check, edit and remove them).
 *
 * The API saves the contact list at once, and the list can change
 * meanwhile (another owner, a manager added by the platform bot), so each
 * change is made to the list as shown and saved with its revision. When
 * someone saved since, the API refuses; the tab reloads the list and the
 * open dialog says so, keeping what was typed for another try.
 */
export function NotificationsTab() {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const mine = useMyNotifications();
  const delivery = useNotificationContacts();
  const list = useManagerContacts();
  const { contacts, isFull, editing, removing } = list;
  const removingContact = removing ?? undefined;

  return (
    <div className="space-y-6">
      <ThisDeviceCard mine={mine} />
      <MyEventsCard mine={mine} />
      {isOwner ? <SetupRemindersCard /> : null}
      <Card
        title={t("settings.contacts.title")}
        description={t("settings.contacts.description")}
        padded={contacts.length === 0}
        actions={
          isOwner ? (
            <Button
              size="sm"
              leadingIcon={<IconPlus className="size-4" aria-hidden />}
              disabled={isFull}
              title={isFull ? t("settings.contacts.limit", { count: MAX_MANAGER_CONTACTS }) : undefined}
              onClick={list.startAdding}
            >
              {t("settings.contacts.add")}
            </Button>
          ) : undefined
        }
      >
        {contacts.length === 0 ? (
          <EmptyState
            className="py-6"
            icon={<IconBell className="size-6" />}
            title={t("settings.contacts.empty")}
            description={t("settings.contacts.emptyDescription")}
          />
        ) : (
          <ul className="divide-y divide-line">
            {contacts.map((contact) => (
              <ContactRow
                key={`${contact.channel}-${contact.address}`}
                contact={contact}
                status={delivery.statusOf(contact)}
                isChecking={delivery.checkingKey !== null && delivery.checkingKey === delivery.statusOf(contact)?.key}
                onTest={(status) => void delivery.sendTest(status)}
                onEdit={() => list.startEditing(contact)}
                onRemove={() => list.startRemoving(contact)}
              />
            ))}
          </ul>
        )}
      </Card>

      {isOwner ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">{t("settings.contacts.telegramLinkHint")}</p>
            <ButtonLink href={businessPath(business.id, "assistant/channels")} variant="secondary" size="sm">
              {t("settings.contacts.openChannels")}
            </ButtonLink>
          </div>
        </Card>
      ) : null}

      <Modal
        open={editing !== null}
        onClose={list.stopEditing}
        title={editing?.original ? t("settings.contacts.editTitle") : t("settings.contacts.addTitle")}
      >
        {editing ? (
          <ContactFormView
            key={editing.original ? contactId(editing.original) : "new"}
            initial={editing.original ?? undefined}
            others={contacts.filter((contact) => !editing.original || contactId(contact) !== contactId(editing.original))}
            languages={languageChoices([business.owner_language], business.languages, ["ka", "ru", "en"])}
            isPending={list.isBusy}
            error={list.dialogError}
            onCancel={list.stopEditing}
            onSubmit={list.onSaveContact}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={removing !== null}
        onClose={list.stopRemoving}
        onConfirm={list.onRemove}
        isPending={list.isBusy}
        error={list.dialogError}
        errorOverrides={STALE_LIST_MESSAGES}
        title={removingContact ? t("settings.contacts.removeTitle", { name: removingContact.name }) : ""}
        confirmLabel={t("settings.contacts.remove")}
      >
        {removingContact ? <p>{t("settings.contacts.removeDescription", { name: removingContact.name })}</p> : null}
      </ConfirmDialog>
    </div>
  );
}

/** A contact's identity in the list: its channel and address. */
function contactId(contact: Pick<ManagerContact, "channel" | "address">): string {
  return `${contact.channel}:${contact.address}`;
}
