import { useQuery } from 'react-query';

import { ApiError, Portfolio } from '@/types';
import { portfolioService } from '@/services/portfolio';

/**
 * Spans every league you are in, so it costs one roster fetch per team on both
 * sides of every matchup. Cached for a couple of minutes rather than refetched
 * on each navigation.
 */
export const usePortfolio = (enabled = true) =>
  useQuery<Portfolio, ApiError>(['portfolio'], () => portfolioService.get(), {
    enabled,
    staleTime: 2 * 60 * 1000,
    retry: false,
  });
