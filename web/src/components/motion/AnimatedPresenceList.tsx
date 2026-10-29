"use client";

/**
 * A list whose items arrive and leave with a short animation while the
 * others slide into the freed space (a resolved handoff, a dismissed toast).
 * Items present on the first render do not animate in.
 *
 *     <AnimatedPresenceList items={handoffs} getKey={(h) => h.id} className="space-y-3"
 *       renderItem={(handoff) => <HandoffCard handoff={handoff} />} />
 */

import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";
import type { Key, ReactNode } from "react";

import { springTransition, tweenTransition } from "@/lib/motion";

const ITEM_MOTION = {
  initial: { opacity: 0, y: -6, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1, transition: springTransition("snappy") },
  exit: { opacity: 0, scale: 0.97, transition: tweenTransition("fast", "exit") },
};

export function AnimatedPresenceList<Item>({
  items,
  getKey,
  renderItem,
  as = "ul",
  className,
  itemClassName,
  "aria-label": ariaLabel,
}: {
  items: readonly Item[];
  getKey: (item: Item) => Key;
  renderItem: (item: Item, index: number) => ReactNode;
  as?: "ul" | "ol" | "div";
  className?: string;
  itemClassName?: string;
  "aria-label"?: string;
}) {
  const List = as;
  const ItemElement = as === "div" ? m.div : m.li;
  return (
    <List className={className} aria-label={ariaLabel}>
      <AnimatePresence initial={false}>
        {items.map((item, index) => (
          <ItemElement
            key={getKey(item)}
            layout="position"
            transition={{ layout: springTransition("layout") }}
            className={itemClassName}
            {...ITEM_MOTION}
          >
            {renderItem(item, index)}
          </ItemElement>
        ))}
      </AnimatePresence>
    </List>
  );
}
