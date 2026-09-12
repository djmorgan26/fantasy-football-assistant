import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { cn } from '@/utils';

type Width = 'narrow' | 'default' | 'wide';

const widths: Record<Width, string> = {
  narrow: 'max-w-2xl',
  default: 'max-w-6xl',
  wide: 'max-w-7xl',
};

/**
 * The page shell. Every route uses it so gutters, max width and vertical
 * rhythm are decided in one place: 16px gutters on a phone, opening up from
 * the small breakpoint onward.
 */
export const PageContainer: React.FC<{
  children: React.ReactNode;
  width?: Width;
  className?: string;
}> = ({ children, width = 'default', className }) => (
  <div className={cn('mx-auto px-4 py-6 sm:px-6 sm:py-8 lg:px-8', widths[width], className)}>
    {children}
  </div>
);

interface PageHeaderProps {
  title: React.ReactNode;
  /** One line under the title. Wraps rather than truncates. */
  subtitle?: React.ReactNode;
  /** A "back" affordance rendered above the title. */
  backTo?: string;
  backLabel?: string;
  /** Leading mark: a team crest, an avatar, a section icon. */
  media?: React.ReactNode;
  /**
   * Drop the mark on phones. Right for a decorative section icon, which only
   * strands itself beside a subtitle that has wrapped to three lines; wrong
   * for a team crest, which is information.
   */
  mediaDesktopOnly?: boolean;
  /** Buttons. They stack full-width on a phone and sit inline from sm: up. */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * Title block for a page. On a phone the title owns the full width and any
 * actions drop beneath it, because a button pinned to the right edge squeezes
 * long league and team names into a column two words wide.
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  backTo,
  backLabel = 'Back',
  media,
  mediaDesktopOnly = false,
  actions,
  className,
}) => (
  <div className={cn('mb-6', className)}>
    {backTo && (
      <Link
        to={backTo}
        className="-ml-1 mb-3 inline-flex min-h-[2.25rem] items-center gap-1 rounded-lg px-1 text-sm font-medium text-fg-muted transition-colors hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeftIcon className="h-4 w-4" />
        {backLabel}
      </Link>
    )}

    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        {media && (
          <div className={cn('shrink-0', mediaDesktopOnly && 'hidden sm:block')}>{media}</div>
        )}
        <div className="min-w-0">
          <h1 className="text-display-sm text-fg">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-fg-muted sm:text-base">{subtitle}</p>}
        </div>
      </div>

      {actions && (
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end">{actions}</div>
      )}
    </div>
  </div>
);
