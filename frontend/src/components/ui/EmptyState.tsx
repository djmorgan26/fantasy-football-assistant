import React from 'react';
import { cn } from '@/utils';

interface EmptyStateProps {
  icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  /** Use the error palette for failure states. */
  variant?: 'default' | 'error';
  className?: string;
}

/**
 * Consistent empty / error / no-results state. Replaces the ad-hoc
 * `text-center py-12 + icon + heading + CTA` blocks scattered across pages.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  variant = 'default',
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-12 text-center', className)}>
      {Icon && (
        <div
          className={cn(
            'mb-4 flex h-14 w-14 items-center justify-center rounded-full',
            variant === 'error'
              ? 'bg-error-100 text-error-600 dark:bg-error-900/40 dark:text-error-300'
              : 'bg-surface-sunken text-fg-subtle'
          )}
        >
          <Icon className="h-7 w-7" />
        </div>
      )}
      <h3 className="font-display text-lg font-bold text-fg">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
};
