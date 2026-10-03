/**
 * Which physical edges of a sideways-scrolling row hide more content: the
 * row fades out there (components/ui/ScrollRow). Right-to-left rows start
 * at their right edge and scroll to negative `scrollLeft` (as every current
 * browser reports it), so their hidden side is mirrored.
 */

export interface ScrollEdges {
  left: boolean;
  right: boolean;
}

/** Half a pixel of rounding is not "more content". */
const SLACK = 1;

export function scrollEdges(scrollLeft: number, scrollWidth: number, clientWidth: number, isRtl: boolean): ScrollEdges {
  const max = Math.max(0, scrollWidth - clientWidth);
  if (max <= SLACK) {
    return { left: false, right: false };
  }
  // Distance scrolled from the row's start, whatever the direction.
  const fromStart = Math.min(max, Math.abs(scrollLeft));
  const startHidden = fromStart > SLACK;
  const endHidden = fromStart < max - SLACK;
  return isRtl ? { left: endHidden, right: startHidden } : { left: startHidden, right: endHidden };
}
