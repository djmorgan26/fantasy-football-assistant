import React from 'react';
import { cn } from '@/utils';

interface BrandMarkProps {
  /** Tailwind sizing, e.g. "h-9 w-9". */
  className?: string;
}

/**
 * The app's logo mark.
 *
 * Deliberately no rounding or background here: the artwork is a squircle tile
 * with its own dark ground and transparent corners, so a `rounded-*` class
 * would clip the curve it already has, and a `bg-*` would show through them.
 *
 * Decorative by default. Every place it appears sits next to the app name or
 * inside a labelled link, so announcing it again would only repeat that.
 */
export const BrandMark: React.FC<BrandMarkProps> = ({ className }) => (
  <img
    src="/logo.png"
    alt=""
    aria-hidden="true"
    width={512}
    height={512}
    className={cn('shrink-0 select-none object-contain', className)}
  />
);
