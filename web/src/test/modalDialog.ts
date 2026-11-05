/**
 * The modal <dialog> of the HTML standard for jsdom, which has the element
 * but neither `showModal()` nor the top layer. What the UI kit relies on,
 * as the standard describes it:
 *
 * - showModal(): the dialog opens as modal (`:modal` matches it), the rest
 *   of the document is blocked (inert), and the dialog focusing steps run:
 *   the first [autofocus] element inside, else the first focusable one;
 * - Escape fires a cancelable "cancel" at the topmost modal dialog, which
 *   closes unless the event was canceled;
 * - close(): the dialog closes, the document is no longer blocked, focus
 *   returns to the element that had it before, and "close" is fired.
 *
 * jsdom's selector engine does not know `:modal`; it is read as the
 * attribute this stand-in sets.
 */

const MODAL_ATTRIBUTE = "data-test-modal";
const FOCUSABLE = "[autofocus], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]";

interface ModalState {
  previousFocus: Element | null;
  blocked: Element[];
}

const states = new WeakMap<HTMLDialogElement, ModalState>();
const stack: HTMLDialogElement[] = [];

function withModalSelector(selectors: string): string {
  return selectors.replaceAll(":modal", `[${MODAL_ATTRIBUTE}]`);
}

/** Everything outside the dialog's ancestor chain becomes inert (blocked by a modal dialog). */
function blockOutside(dialog: HTMLDialogElement): Element[] {
  const blocked: Element[] = [];
  for (let node: Element | null = dialog; node && node !== document.body; node = node.parentElement) {
    for (const sibling of node.parentElement?.children ?? []) {
      if (sibling !== node && !sibling.hasAttribute("inert")) {
        sibling.setAttribute("inert", "");
        blocked.push(sibling);
      }
    }
  }
  return blocked;
}

function focusInside(dialog: HTMLDialogElement): void {
  const target = dialog.querySelector<HTMLElement>("[autofocus]") ?? dialog.querySelector<HTMLElement>(FOCUSABLE) ?? dialog;
  target.focus();
}

function topModal(): HTMLDialogElement | undefined {
  return stack.at(-1);
}

/** Forget the dialogs of a finished test (its DOM is gone). */
export function resetModalDialogs(): void {
  stack.length = 0;
}

export function installModalDialog(): void {
  const proto = HTMLDialogElement.prototype;
  if (typeof proto.showModal === "function") {
    return;
  }

  proto.showModal = function showModal(this: HTMLDialogElement) {
    if (this.open && states.has(this)) {
      return;
    }
    if (this.open || !this.isConnected) {
      throw new DOMException("The dialog cannot be shown as modal.", "InvalidStateError");
    }
    const previousFocus = document.activeElement;
    this.setAttribute("open", "");
    this.setAttribute(MODAL_ATTRIBUTE, "");
    states.set(this, { previousFocus, blocked: blockOutside(this) });
    stack.push(this);
    focusInside(this);
  };

  proto.show = function show(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };

  proto.close = function close(this: HTMLDialogElement, returnValue?: string) {
    if (!this.open) {
      return;
    }
    if (returnValue !== undefined) {
      this.returnValue = returnValue;
    }
    this.removeAttribute("open");
    this.removeAttribute(MODAL_ATTRIBUTE);
    const state = states.get(this);
    states.delete(this);
    stack.splice(stack.indexOf(this), 1);
    for (const element of state?.blocked ?? []) {
      element.removeAttribute("inert");
    }
    if (state?.previousFocus instanceof HTMLElement && state.previousFocus.isConnected) {
      state.previousFocus.focus();
    }
    this.dispatchEvent(new Event("close"));
  };

  document.addEventListener("keydown", (event) => {
    const dialog = topModal();
    if (event.key !== "Escape" || !dialog) {
      return;
    }
    const cancel = new Event("cancel", { cancelable: true });
    if (dialog.dispatchEvent(cancel)) {
      dialog.close();
    }
  });

  const matches = Element.prototype.matches;
  Element.prototype.matches = function patchedMatches(this: Element, selectors: string) {
    return matches.call(this, withModalSelector(selectors));
  };
  const elementQueryAll = Element.prototype.querySelectorAll;
  Element.prototype.querySelectorAll = function patchedQueryAll(this: Element, selectors: string) {
    return elementQueryAll.call(this, withModalSelector(selectors));
  } as typeof Element.prototype.querySelectorAll;
  const documentQueryAll = Document.prototype.querySelectorAll;
  Document.prototype.querySelectorAll = function patchedQueryAll(this: Document, selectors: string) {
    return documentQueryAll.call(this, withModalSelector(selectors));
  } as typeof Document.prototype.querySelectorAll;
}
