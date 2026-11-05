"use client";

import { useEffect, useRef, type MouseEvent, type RefObject, type SyntheticEvent } from "react";

export interface ModalDialogProps {
  ref: RefObject<HTMLDialogElement | null>;
  onClose: () => void;
  onCancel: (event: SyntheticEvent<HTMLDialogElement>) => void;
  onMouseDown: (event: MouseEvent<HTMLDialogElement>) => void;
}

/**
 * Drives a native <dialog> as a modal from an `open` flag (Modal, Drawer,
 * the phone menu): spread the result on the element.
 *
 * `onClose` runs only when the person closes it: Escape, a press on the
 * backdrop, or the browser closing it on its own. Turning `open` to false
 * closes the dialog without calling `onClose`, so a screen can swap one
 * dialog for another without the first one's handler firing late.
 */
export function useModalDialog(open: boolean, onClose: () => void): ModalDialogProps {
  const ref = useRef<HTMLDialogElement>(null);
  // What the parent asked for. The native "close" event of a programmatic
  // close (open → false) arrives when this is already false.
  const isOpenRequested = useRef(open);

  useEffect(() => {
    isOpenRequested.current = open;
    const dialog = ref.current;
    if (!dialog) {
      return;
    }
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return {
    ref,
    onClose: () => {
      // E.g. a second Escape, which browsers may not let a page cancel.
      if (isOpenRequested.current) {
        onClose();
      }
    },
    onCancel: (event) => {
      event.preventDefault();
      onClose();
    },
    onMouseDown: (event) => {
      // A press on the backdrop (the dialog element itself) closes it.
      if (event.target === event.currentTarget) {
        onClose();
      }
    },
  };
}
