import React from 'react';
import { cn } from '@/utils';

/**
 * A dark band naming the tool and the context it is showing.
 *
 * Borrowed from how the big fantasy sites open every tool: a saturated header
 * stating exactly what you are looking at ("Starting Lineup — Week 14 — PPR"),
 * with the controls that change that context sitting inside it, then light,
 * dense content below. The figure/ground split does most of the orienting work
 * on a page that is otherwise a stack of similar cards.
 *
 * The band is the dark theme's own surface colour, so it reads as deliberate in
 * both themes rather than as an inverted patch.
 */
interface ToolHeaderProps {
  title: React.ReactNode;
  /** Week, scoring format, team — the state the tool is currently showing. */
  context?: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  /** Selectors and buttons that change what the tool shows. */
  actions?: React.ReactNode;
  className?: string;
}

export const ToolHeader: React.FC<ToolHeaderProps> = ({
  title,
  context,
  subtitle,
  icon: Icon,
  actions,
  className,
}) => (
  <div
    className={cn(
      'rounded-card bg-[#16221C] px-4 py-4 text-[#EDF1EC] shadow-elevation-2 sm:px-6 sm:py-5',
      'dark:border dark:border-border',
      className
    )}
  >
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        {Icon && (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10">
            <Icon className="h-5 w-5 text-[#7FD6A0]" />
          </span>
        )}
        <div className="min-w-0">
          <h2 className="flex flex-wrap items-baseline gap-x-2 font-display text-lg font-bold leading-tight sm:text-xl">
            <span className="truncate">{title}</span>
            {context && (
              <span className="text-sm font-semibold text-[#7FD6A0]">{context}</span>
            )}
          </h2>
          {subtitle && <p className="mt-0.5 text-sm text-[#A9BBB0]">{subtitle}</p>}
        </div>
      </div>

      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      )}
    </div>
  </div>
);
