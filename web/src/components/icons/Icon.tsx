/**
 * The frame of every cabinet icon: 24×24 outline, stroke = currentColor.
 * Size icons with classes (`className="size-5"`) and hide decorative ones
 * from screen readers with `aria-hidden`.
 */

import type { SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement>;

export function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}
