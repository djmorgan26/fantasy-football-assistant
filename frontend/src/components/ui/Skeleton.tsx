import React from 'react';
import { cn } from '@/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

/** Shimmering placeholder block. Compose with width/height utilities. */
export const Skeleton: React.FC<SkeletonProps> = ({ className, ...props }) => {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-surface-sunken', className)}
      aria-hidden="true"
      {...props}
    />
  );
};

/** A few lines of placeholder text. */
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className,
}) => (
  <div className={cn('space-y-2', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')} />
    ))}
  </div>
);

/** A card-shaped placeholder. */
export const SkeletonCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={cn('rounded-card border border-border bg-surface-raised p-6', className)}>
    <Skeleton className="mb-4 h-5 w-1/3" />
    <SkeletonText lines={3} />
  </div>
);

/**
 * A stack of equal placeholder rows, for a list whose shape is already known:
 * a roster, search results, a board of players. Matching the real row height
 * is the point — a spinner of unknown size collapses the page and then shoves
 * it back down when the data lands.
 */
export const SkeletonList: React.FC<{
  rows?: number;
  /** Tailwind height of one row. Match whatever it is standing in for. */
  height?: string;
  className?: string;
}> = ({ rows = 5, height = 'h-16', className }) => (
  <div className={cn('space-y-3', className)} role="status" aria-label="Loading">
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className={cn('w-full rounded-lg', height)} />
    ))}
  </div>
);

/** A grid of skeleton cards for list/loading states. */
export const SkeletonGrid: React.FC<{ count?: number; className?: string }> = ({
  count = 6,
  className,
}) => (
  <div className={cn('grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3', className)}>
    {Array.from({ length: count }).map((_, i) => (
      <SkeletonCard key={i} />
    ))}
  </div>
);
