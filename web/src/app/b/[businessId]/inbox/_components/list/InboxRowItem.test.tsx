import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale } from "@/test/render";

import { business } from "../../../settings/_lib/settingsFixtures";
import type { InboxRow } from "../../_lib/inboxModel";
import { InboxRowItem, type RowEvents, type RowState } from "./InboxRowItem";

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const row: InboxRow = {
  id: "conversation-1",
  contactName: "Lukas Weber",
  contactPhone: null,
  channel: "web_chat",
  language: "en",
  status: "open",
  isAfterHours: false,
  isSandbox: false,
  lastMessageText: "Is there a table at eight?",
  lastMessageAttachment: null,
  lastMessageAuthor: "customer",
  lastMessageAt: 0,
  isAssignedAutomatically: false,
  noteCount: 0,
  handoff: null,
  request: null,
  rating: null,
};

const state: RowState = {
  density: "comfortable",
  isOpen: false,
  isCursor: false,
  isChecked: false,
  isSelectable: false,
  isSelecting: false,
  isBusy: false,
};

function renderRow(): { events: RowEvents; link: HTMLElement } {
  const events: RowEvents = { onToggle: vi.fn(), onHint: vi.fn(), onCursor: vi.fn() };
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <ul>
        <InboxRowItem row={row} position={0} member={null} state={state} events={events} linkQuery="" nowMs={0} />
      </ul>
    </BusinessProvider>,
  );
  return { events, link: screen.getByRole("link") };
}

/** Focus as the keyboard brings it (Tab, j/k): the browser marks it :focus-visible. */
function asKeyboardFocus(): void {
  const matches = Element.prototype.matches;
  vi.spyOn(Element.prototype, "matches").mockImplementation(function (this: Element, selector: string) {
    return selector === ":focus-visible" || matches.call(this, selector);
  });
}

describe("an inbox row taking the focus", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("from the keyboard takes the cursor and shows its details at once", () => {
    asKeyboardFocus();
    const { events, link } = renderRow();

    fireEvent.focus(link);

    expect(events.onCursor).toHaveBeenCalledWith(row);
    expect(events.onHint).toHaveBeenCalledWith(row, link);
  });

  it("from a tap leaves the list alone until the tap has painted, and shows no details", async () => {
    const { events, link } = renderRow();

    fireEvent.focus(link);

    // Moving the cursor redraws the whole list: inside the tap it would hold the tap's answer back.
    expect(events.onCursor).not.toHaveBeenCalled();
    await waitFor(() => expect(events.onCursor).toHaveBeenCalledWith(row));
    expect(events.onHint).not.toHaveBeenCalled();
  });
});
