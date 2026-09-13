import React from 'react';
import { cn } from '@/utils';
import { ReactionKind } from '@/types';

/**
 * Five typed reactions rather than a thumbs up / thumbs down.
 *
 * A binary records *that* a post landed. These record *how* — and "how" is the
 * only part a voice profile can learn anything from. The weights are the same
 * ones the server scores with, shown here so the league can see that a cold
 * take genuinely costs a post its place in the AI's material.
 */
export const REACTIONS: {
  kind: ReactionKind;
  glyph: string;
  label: string;
  weight: number;
}[] = [
  { kind: 'savage', glyph: '🔥', label: 'Savage', weight: 3 },
  { kind: 'funny', glyph: '😂', label: 'Funny', weight: 3 },
  { kind: 'brutal', glyph: '💀', label: 'Brutal', weight: 2 },
  { kind: 'smart', glyph: '🤓', label: 'Actually smart', weight: 2 },
  { kind: 'cold', glyph: '🧊', label: 'Cold take', weight: -2 },
];

interface ReactionBarProps {
  counts: Record<ReactionKind, number>;
  mine: ReactionKind[];
  onReact: (reaction: ReactionKind) => void;
  disabled?: boolean;
  className?: string;
}

export const ReactionBar: React.FC<ReactionBarProps> = ({
  counts,
  mine,
  onReact,
  disabled,
  className,
}) => (
  <div className={cn('rail gap-1.5 sm:flex-wrap sm:overflow-visible', className)}>
    {REACTIONS.map(({ kind, glyph, label }) => {
      const count = counts?.[kind] ?? 0;
      const active = mine.includes(kind);
      return (
        <button
          key={kind}
          type="button"
          onClick={() => onReact(kind)}
          disabled={disabled}
          aria-pressed={active}
          aria-label={active ? `Remove ${label} reaction` : `React: ${label}`}
          title={label}
          className={cn(
            'inline-flex min-h-[2.25rem] shrink-0 items-center gap-1.5 rounded-pill border px-2.5',
            'text-sm font-semibold transition-colors focus:outline-none',
            'focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50',
            active
              ? 'border-brand bg-brand/10 text-brand'
              : 'border-border text-fg-muted hover:border-border-strong hover:bg-surface-sunken hover:text-fg'
          )}
        >
          <span aria-hidden className="text-base leading-none">
            {glyph}
          </span>
          {count > 0 && <span className="tabular">{count}</span>}
        </button>
      );
    })}
  </div>
);
