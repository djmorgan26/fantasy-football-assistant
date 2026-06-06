import React, { useMemo, useState } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useLeagueValueBoard } from '@/hooks/useDraft';
import { ValueBoardPlayer } from '@/types';
import { cn } from '@/utils';
import {
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

const POSITIONS = ['ALL', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'] as const;

const POSITION_COLORS: Record<string, string> = {
  QB: 'bg-red-100 text-red-800',
  RB: 'bg-green-100 text-green-800',
  WR: 'bg-blue-100 text-blue-800',
  TE: 'bg-orange-100 text-orange-800',
  K: 'bg-purple-100 text-purple-800',
  DEF: 'bg-gray-200 text-gray-800',
};

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
        <CardContent>
          <div className="text-center py-12">
            <ExclamationTriangleIcon className="h-10 w-10 text-yellow-500 mx-auto mb-3" />
            <p className="text-gray-700 font-medium">Couldn't build the draft board</p>
            <p className="text-sm text-gray-500 mt-1">
              {error?.detail ||
                'Make sure this is a Sleeper league and projections are available for the season.'}
            </p>
          </div>
        </CardContent>
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
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {pos}
            </button>
          ))}
        </div>
        <div className="relative flex-1 sm:max-w-xs">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search players..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-500">
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
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs tracking-wide">
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
            <tbody className="divide-y divide-gray-100">
              {filtered.map((p) => (
                <tr key={p.player_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500 tabular-nums">{p.overall_rank}</td>
                  <td className="px-4 py-2 font-medium text-gray-900">
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
                        POSITION_COLORS[p.position] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {p.position}
                      {p.position_rank ? <span className="ml-0.5">{p.position_rank}</span> : null}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-600">{p.team || '—'}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-gray-900">
                    {p.projected_points.toFixed(1)}
                  </td>
                  <td
                    className={cn(
                      'px-4 py-2 text-right tabular-nums font-semibold',
                      p.vbd > 0 ? 'text-green-600' : 'text-gray-400'
                    )}
                  >
                    {p.vbd > 0 ? `+${p.vbd.toFixed(1)}` : p.vbd.toFixed(1)}
                  </td>
                  <td className="px-4 py-2 text-center text-gray-600">{p.tier ?? '—'}</td>
                  <td className="px-4 py-2 text-right text-gray-500 tabular-nums">
                    {p.adp ?? '—'}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-gray-500">
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
