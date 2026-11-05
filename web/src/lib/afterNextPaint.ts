/**
 * Runs `task` once the browser has painted the next frame (a frame, then a
 * task after it) and returns a function that cancels it. For work a tap
 * starts that may hold the main thread (a page redrawing for a new choice,
 * a sheet opening): the tap's own feedback paints first, so its time to the
 * next paint stays short on a slow phone (INP, e2e/motion-budget.spec.ts).
 */
export function afterNextPaint(task: () => void): () => void {
  let timer: number | undefined;
  const frame = window.requestAnimationFrame(() => {
    timer = window.setTimeout(task, 0);
  });
  return () => {
    window.cancelAnimationFrame(frame);
    window.clearTimeout(timer);
  };
}
