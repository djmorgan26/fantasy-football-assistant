import React from 'react';
import { CheckIcon } from '@heroicons/react/24/outline';
import { Badge } from '@/components/ui';
import { MarketPlayer } from '@/types';
import { cn } from '@/utils';

const POSITION_TONE: Record<string, string> = {
  QB: 'bg-error-100 text-error-800 dark:bg-error-900/40 dark:text-error-300',
  RB: 'bg-success-100 text-success-800 dark:bg-success-900/40 dark:text-success-300',
  WR: 'bg-brand/10 text-brand',
  TE: 'bg-warning-100 text-warning-800 dark:bg-warning-900/40 dark:text-warning-300',
  K: 'bg-surface-sunken text-fg-muted',
  DEF: 'bg-surface-sunken text-fg-muted',
};

/**
 * Pick players off a real roster.
 *
 * This replaces three numeric inputs labelled "ESPN Player ID", which required
 * the user to go and read an undocumented API response to use the feature at
 * all. Players are listed best first with their projection and trade value, so
 * the choice can be made here rather than in another tab.
 */
export const PlayerPicker: React.FC<{
  players: MarketPlayer[];
  selected: string[];
  onToggle: (playerId: string) => void;
  emptyLabel?: string;
}> = ({ players, selected, onToggle, emptyLabel = 'No players on this roster' }) => {
  if (players.length === 0) {
    return <p className="py-4 text-sm text-fg-muted">{emptyLabel}</p>;
  }

  return (
    <ul className="max-h-80 space-y-1 overflow-y-auto pr-1" role="listbox" aria-multiselectable>
      {players.map((player) => {
        const isSelected = selected.includes(player.player_id);
        const injured =
          player.injury_status &&
          !['ACTIVE', 'NA', 'NONE'].includes(player.injury_status.toUpperCase());

        return (
          <li key={player.player_id}>
            <button
              type="button"
              role="option"
              aria-selected={isSelected}
              onClick={() => onToggle(player.player_id)}
              className={cn(
                'flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isSelected
                  ? 'border-brand bg-brand/5'
                  : 'border-transparent hover:border-border hover:bg-surface-sunken'
              )}
            >
              <span
                className={cn(
                  'flex h-5 w-5 shrink-0 items-center justify-center rounded border',
                  isSelected ? 'border-brand bg-brand text-white' : 'border-border-strong'
                )}
                aria-hidden="true"
              >
                {isSelected && <CheckIcon className="h-3.5 w-3.5" />}
              </span>

              <span
                className={cn(
                  'w-11 shrink-0 rounded px-1.5 py-0.5 text-center text-[11px] font-bold',
                  POSITION_TONE[player.position] ?? 'bg-surface-sunken text-fg-muted'
                )}
              >
                {player.position}
              </span>

              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-medium text-fg">
                    {player.full_name}
                  </span>
                  {player.is_starter && (
                    <Badge variant="default" size="sm" className="shrink-0 px-1.5 py-0 text-[10px]">
                      ST
                    </Badge>
                  )}
                  {injured && (
                    <Badge variant="error" size="sm" className="shrink-0 px-1.5 py-0 text-[10px]">
                      {player.injury_status}
                    </Badge>
                  )}
                </span>
                <span className="text-xs text-fg-muted">
                  {player.pro_team || 'FA'} · {player.projected_points.toFixed(1)} proj
                </span>
              </span>

              <span className="shrink-0 text-right">
                <span className="tabular block text-sm font-semibold text-fg">
                  {player.value.toFixed(1)}
                </span>
                <span className="block text-[10px] uppercase tracking-wide text-fg-muted">
                  value
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
};
