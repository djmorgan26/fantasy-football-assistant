import React from 'react';
import { cn } from '@/utils';

export interface TabItem {
  key: string;
  label: React.ReactNode;
  icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
}

interface TabsProps {
  tabs: TabItem[];
  value: string;
  onChange: (key: string) => void;
  className?: string;
  /** 'underline' (default) for page-level, 'pill' for compact toggles. */
  variant?: 'underline' | 'pill';
  'aria-label'?: string;
}

/**
 * Accessible tab strip. Controlled via value/onChange so it works with
 * routing or local state. Roving focus + arrow keys handled here.
 */
export const Tabs: React.FC<TabsProps> = ({
  tabs,
  value,
  onChange,
  className,
  variant = 'underline',
  'aria-label': ariaLabel,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const dir = e.key === 'ArrowRight' ? 1 : -1;
    const next = (index + dir + tabs.length) % tabs.length;
    onChange(tabs[next].key);
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        variant === 'underline'
          ? 'flex gap-1 border-b border-border'
          : 'inline-flex gap-1 rounded-lg bg-surface-sunken p-1',
        className
      )}
    >
      {tabs.map((tab, i) => {
        const active = tab.key === value;
        const Icon = tab.icon;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.key)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            className={cn(
              'inline-flex items-center gap-2 whitespace-nowrap text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              variant === 'underline'
                ? cn(
                    '-mb-px border-b-2 px-4 py-2.5',
                    active
                      ? 'border-brand text-brand'
                      : 'border-transparent text-fg-muted hover:border-border-strong hover:text-fg'
                  )
                : cn(
                    'rounded-md px-3 py-1.5',
                    active
                      ? 'bg-surface-raised text-fg shadow-elevation-1'
                      : 'text-fg-muted hover:text-fg'
                  )
            )}
          >
            {Icon && <Icon className="h-4 w-4" />}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
