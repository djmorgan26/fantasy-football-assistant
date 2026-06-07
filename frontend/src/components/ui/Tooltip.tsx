import React, { useId, useState } from 'react';
import { cn } from '@/utils';

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: 'top' | 'bottom';
  className?: string;
}

/**
 * Lightweight hover/focus tooltip with aria-describedby. CSS-only positioning;
 * for simple stat explanations and value-board deltas.
 */
export const Tooltip: React.FC<TooltipProps> = ({ content, children, side = 'top', className }) => {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-flex">
      {React.cloneElement(children, {
        'aria-describedby': open ? id : undefined,
        onMouseEnter: () => setOpen(true),
        onMouseLeave: () => setOpen(false),
        onFocus: () => setOpen(true),
        onBlur: () => setOpen(false),
      })}
      {open && (
        <span
          role="tooltip"
          id={id}
          className={cn(
            'pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-md bg-fg px-2 py-1 text-xs font-medium text-surface-raised shadow-elevation-3',
            side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5',
            className
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
};
