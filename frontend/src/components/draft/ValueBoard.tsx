import React, { useMemo, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { useLeagueValueBoard } from '@/hooks/useDraft';
import { ValueBoardPlayer } from '@/types';
import { cn, getPositionColor } from '@/utils';
import {
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const POSITIONS = ['ALL', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'] as const;

interface ValueBoardProps {
  leagueId: number;
}

export const ValueBoard: React.FC<ValueBoardProps> = ({ leagueId }) => {
  const { data, isLoading, error } = useLeagueValueBoard(leagueId);
  const [position, setPosition] = useState<(typeof POSITIONS)[number]>('ALL');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!data) return [] as ValueBoardPlayer[];
    const q = search.trim().toLowerCase();
    return data.players.filter((p) => {
      if (position !== 'ALL' && p.position !== position) return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, position, search]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <EmptyState
          variant="error"
          icon={ExclamationTriangleIcon}
          title="Couldn't build the draft board"
          description={
            error?.detail ||
            'Make sure this is a Sleeper league and projections are available for the season.'
          }
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {POSITIONS.map((pos) => (
            <button
              key={pos}
              onClick={() => setPosition(pos)}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                position === pos
                  ? 'bg-brand text-brand-fg'
                  : 'bg-surface-sunken text-fg-muted hover:bg-border'
              )}
            >
              {pos}
            </button>
          ))}
        </div>
        <div className="relative flex-1 sm:max-w-xs">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-fg-subtle" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search players..."
            className="w-full pl-9 pr-3 py-2 bg-surface-raised border border-border rounded-md text-sm text-fg placeholder:text-fg-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-fg-muted">
        <span>
          {filtered.length} players · {data.season} ·{' '}
          <span className="capitalize">{data.scoring}</span> scoring · {data.team_count} teams
        </span>
        <span className="hidden sm:inline">VBD = value over replacement starter</span>
      </div>

      {/* Table */}
      <Card padding={false}>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-surface-sunken text-fg-muted uppercase text-xs tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Rank</th>
                <th className="px-4 py-3 text-left">Player</th>
                <th className="px-4 py-3 text-left">Pos</th>
                <th className="px-4 py-3 text-left">Team</th>
                <th className="px-4 py-3 text-right">Proj</th>
                <th className="px-4 py-3 text-right">VBD</th>
                <th className="px-4 py-3 text-center">Tier</th>
                <th className="px-4 py-3 text-right">ADP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((p) => (
                <tr key={p.player_id} className="hover:bg-surface-sunken">
                  <td className="px-4 py-2 text-fg-muted tabular">{p.overall_rank}</td>
                  <td className="px-4 py-2 font-medium text-fg">
                    {p.name}
                    {p.injury_status && (
                      <Badge variant="error" size="sm" className="ml-2">
                        {p.injury_status}
                      </Badge>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
                        getPositionColor(p.position)
                      )}
                    >
                      {p.position}
                      {p.position_rank ? <span className="ml-0.5">{p.position_rank}</span> : null}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-fg-muted">{p.team || '—'}</td>
                  <td className="px-4 py-2 text-right tabular text-fg">
                    {p.projected_points.toFixed(1)}
                  </td>
                  <td
                    className={cn(
                      'px-4 py-2 text-right tabular font-semibold',
                      p.vbd > 0 ? 'text-success-600' : 'text-fg-subtle'
                    )}
                  >
                    {p.vbd > 0 ? `+${p.vbd.toFixed(1)}` : p.vbd.toFixed(1)}
                  </td>
                  <td className="px-4 py-2 text-center text-fg-muted">{p.tier ?? '—'}</td>
                  <td className="px-4 py-2 text-right text-fg-muted tabular">
                    {p.adp ?? '—'}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-fg-muted">
                    No players match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
