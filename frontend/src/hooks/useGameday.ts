import { useQuery } from 'react-query';

import { ApiError, GameDay } from '@/types';
import { gamedayService } from '@/services/gameday';

/**
 * Scores move while you watch, so this refetches on an interval rather than
 * waiting for a navigation. Two minutes is frequent enough to feel live without
 * re-pulling every roster in the league every few seconds.
 */
export const useGameday = (leagueId: number, enabled = true) =>
  useQuery<GameDay, ApiError>(
    ['gameday', leagueId],
    () => gamedayService.get(leagueId),
    {
      enabled: enabled && !!leagueId,
      staleTime: 60 * 1000,
      refetchInterval: 2 * 60 * 1000,
      refetchOnWindowFocus: true,
      retry: false,
    }
  );
