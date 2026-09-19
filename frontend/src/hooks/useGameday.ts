import { useQuery } from 'react-query';

import { ApiError, GameDay } from '@/types';
import { gamedayService } from '@/services/gameday';

/** A game in progress is worth checking on far more often than a quiet slate. */
export const LIVE_INTERVAL = 30 * 1000;
export const IDLE_INTERVAL = 2 * 60 * 1000;

/**
 * How often to go back for scores.
 *
 * A fixed interval is wrong in both directions: every two minutes is too slow
 * while a game is being played, and too eager on a Tuesday when nothing can
 * possibly have changed. So the slate decides — if anything is live, poll like
 * it; otherwise idle.
 */
export const pollInterval = (live: boolean) => (live ? LIVE_INTERVAL : IDLE_INTERVAL);

/**
 * Scores move while you watch, so this refetches on an interval rather than
 * waiting for a navigation, and again whenever you come back to the tab.
 */
export const useGameday = (leagueId: number, enabled = true) =>
  useQuery<GameDay, ApiError>(
    ['gameday', leagueId],
    () => gamedayService.get(leagueId),
    {
      enabled: enabled && !!leagueId,
      // Coming back to the tab should show current scores, not whatever was on
      // screen when you left it.
      staleTime: 15 * 1000,
      refetchInterval: (data) =>
        pollInterval(!!data?.games.some((game) => game.state === 'in')),
      refetchOnWindowFocus: true,
      // Polling in a hidden tab burns the phone's battery for nobody; react-query
      // resumes it, and refetches once, the moment the tab is looked at again.
      refetchIntervalInBackground: false,
      // Deliberately no keepPreviousData: a poll keeps the scores on screen
      // regardless, and the one case it would change is switching leagues,
      // where it would show the league you just left as though it were the one
      // you opened.
      retry: false,
    }
  );
