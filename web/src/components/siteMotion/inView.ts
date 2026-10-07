/**
 * "Tell me once this element is on screen": one IntersectionObserver per
 * share of visibility serves every reveal of the page, and an element is
 * forgotten as soon as it has been seen (content that arrived stays).
 */

type OnSeen = () => void;

const observers = new Map<number, IntersectionObserver>();
const waiting = new Map<Element, OnSeen>();

function observerFor(amount: number): IntersectionObserver {
  const existing = observers.get(amount);
  if (existing) {
    return existing;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const onSeen = waiting.get(entry.target);
        if (entry.isIntersecting && onSeen) {
          observer.unobserve(entry.target);
          waiting.delete(entry.target);
          onSeen();
        }
      }
    },
    { threshold: amount },
  );
  observers.set(amount, observer);
  return observer;
}

/**
 * Calls `onSeen` once, when `amount` (0–1) of `element` is visible; at once
 * where the browser cannot tell. Returns the function that stops waiting.
 */
export function onceInView(element: Element, amount: number, onSeen: OnSeen): () => void {
  if (typeof IntersectionObserver === "undefined") {
    onSeen();
    return () => {};
  }
  const observer = observerFor(amount);
  waiting.set(element, onSeen);
  observer.observe(element);
  return () => {
    waiting.delete(element);
    observer.unobserve(element);
  };
}
