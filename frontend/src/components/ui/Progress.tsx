import React from 'react';
import { cn } from '@/utils';

interface ProgressProps {
  /** 0-100 */
  value: number;
  className?: string;
  /** Bar color. Defaults to brand; pass a token class for status coloring. */
  barClassName?: string;
  size?: 'sm' | 'md';
  label?: string;
}

/** Determinate progress bar (waiver budget, win %, draft clock). */
export const Progress: React.FC<ProgressProps> = ({
  value,
  className,
  barClassName,
  size = 'md',
  label,
}) => {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn(
        'w-full overflow-hidden rounded-pill bg-surface-sunken',
        size === 'sm' ? 'h-1.5' : 'h-2.5',
        className
      )}
    >
      <div
        className={cn('h-full rounded-pill bg-brand transition-all duration-500', barClassName)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
};
