"use client";

/** The chat widget's host element in the page's chat container. */
const WIDGET_HOST = "[data-assistant-workshop-chat]";
const WIDGET_INPUT = "textarea.aw-input";

/**
 * "Book" for a business that books through its chat: the visitor's message
 * field gets a first line ("Hello! I'd like to book.") to edit and send,
 * and the focus. Before the chat is up it only brings the chat into view.
 */
export function BookInChatButton({ label, prompt, containerId }: { label: string; prompt: string; containerId: string }) {
  function startBooking() {
    const container = document.getElementById(containerId);
    const input = container?.querySelector(WIDGET_HOST)?.shadowRoot?.querySelector<HTMLTextAreaElement>(WIDGET_INPUT);
    if (!input) {
      container?.scrollIntoView({ block: "nearest" });
      return;
    }
    if (input.value.trim() === "") {
      input.value = prompt;
      // The widget enables its Send button on input.
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    input.scrollIntoView({ block: "nearest" });
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }

  return (
    <button type="button" className="hc-info-book" onClick={startBooking}>
      {label}
    </button>
  );
}
