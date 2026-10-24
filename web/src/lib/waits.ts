/**
 * Waits that run one after another and can be cancelled together: "once
 * the page has loaded, then when the browser is idle, then when the hero is
 * on screen". A wait calls `next` when its moment comes (a second call is
 * ignored) and returns what cancels it.
 */

export type Wait = (next: () => void) => () => void;

/**
 * Runs `waits` in order, then `done`. The returned function cancels the
 * wait in progress; nothing runs after it, even a wait that calls `next`
 * late.
 */
export function inSequence(waits: readonly Wait[], done: () => void): () => void {
  let current = 0;
  let isCancelled = false;
  let cancelCurrent: (() => void) | undefined;

  const run = (index: number) => {
    if (isCancelled) {
      return;
    }
    current = index;
    cancelCurrent = undefined;
    const wait = waits[index];
    if (wait === undefined) {
      done();
      return;
    }
    const cancel = wait(() => {
      if (current === index && !isCancelled) {
        run(index + 1);
      }
    });
    // A wait that called `next` straight away has already moved on.
    if (current === index) {
      cancelCurrent = cancel;
    }
  };

  run(0);
  return () => {
    isCancelled = true;
    cancelCurrent?.();
  };
}
