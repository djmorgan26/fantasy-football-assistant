import React from 'react';
import { cn } from '@/utils';

// Custom platform identity chips. We intentionally do not ship official
// ESPN or Sleeper logo artwork (trademarked); platform names are used only
// to identify which service a league is connected to, with our own marks
// and brand-evocative colors.

type PlatformKey = 'espn' | 'sleeper' | 'unknown';

interface PlatformStyle {
  label: string;
  monogram: string;
  chip: string;
  mark: string;
}

const PLATFORM_STYLES: Record<PlatformKey, PlatformStyle> = {
  espn: {
    label: 'ESPN',
    monogram: 'E',
    chip: 'bg-[#cc0000]/10 text-[#a30000] dark:bg-[#ff5c5c]/15 dark:text-[#ff8a8a]',
    mark: 'bg-[#cc0000] text-white',
  },
  sleeper: {
    label: 'Sleeper',
    monogram: 'S',
    chip: 'bg-[#4f46e5]/10 text-[#4338ca] dark:bg-[#818cf8]/15 dark:text-[#a5b4fc]',
    mark: 'bg-[#4f46e5] text-white',
  },
  unknown: {
    label: 'League',
    monogram: '?',
    chip: 'bg-surface-sunken text-fg-muted',
    mark: 'bg-border text-fg-muted',
  },
};

export const normalizePlatform = (platform?: string | null): PlatformKey => {
  const value = (platform || '').trim().toLowerCase();
  if (value === 'espn') return 'espn';
  if (value === 'sleeper') return 'sleeper';
  return 'unknown';
};

interface PlatformBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  platform?: string | null;
  size?: 'sm' | 'md';
}

export const PlatformBadge: React.FC<PlatformBadgeProps> = ({
  platform,
  size = 'sm',
  className,
  ...props
}) => {
  const style = PLATFORM_STYLES[normalizePlatform(platform)];

  const chipSizes = {
    sm: 'pl-1 pr-2 py-0.5 text-xs gap-1.5',
    md: 'pl-1.5 pr-2.5 py-1 text-sm gap-2',
  };

  const markSizes = {
    sm: 'h-4 w-4 text-[0.6rem]',
    md: 'h-5 w-5 text-xs',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-semibold transition-colors',
        style.chip,
        chipSizes[size],
        className
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          'flex flex-shrink-0 items-center justify-center rounded-full font-bold leading-none',
          style.mark,
          markSizes[size]
        )}
      >
        {style.monogram}
      </span>
      {style.label}
    </span>
  );
};
