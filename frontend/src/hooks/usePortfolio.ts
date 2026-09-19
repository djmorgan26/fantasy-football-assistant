import { useQuery } from 'react-query';

import { ApiError, Portfolio } from '@/types';
import { portfolioService } from '@/services/portfolio';
import { pollInterval } from './useGameday';

/**
 * Every team you run, and the live slate underneath them.
 *
 * It spans every league, so it costs one roster fetch per team on both sides
 * of every matchup — but it is also the screen somebody leaves open through a
 * Sunday afternoon, so it polls on the same cadence Game Day does: quickly
 * while games are being played, slowly when they are not.
 */
export const usePortfolio = (enabled = true) =>
  useQuery<Portfolio, ApiError>(['portfolio'], () => portfolioService.get(), {
    enabled,
    staleTime: 15 * 1000,
    refetchInterval: (data) => pollInterval((data?.live?.games ?? 0) > 0),
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
    retry: false,
  });
