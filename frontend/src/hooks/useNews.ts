import { useMutation, useQuery } from 'react-query';
import toast from 'react-hot-toast';

import {
  ApiError,
  LeagueNews,
  NewsArticle,
  NewsDigest,
  ScoreboardGame,
  TrendingPlayer,
} from '@/types';
import { newsService } from '@/services/news';

export const useLeagueNews = (leagueId: number) =>
  useQuery<LeagueNews, ApiError>(
    ['news', 'league', leagueId],
    () => newsService.leagueNews(leagueId),
    { enabled: !!leagueId, staleTime: 5 * 60 * 1000 }
  );

export const useWire = () =>
  useQuery<NewsArticle[], ApiError>(['news', 'wire'], () => newsService.wire(), {
    staleTime: 5 * 60 * 1000,
  });

export const useTrending = (kind: 'add' | 'drop' = 'add') =>
  useQuery<TrendingPlayer[], ApiError>(
    ['news', 'trending', kind],
    () => newsService.trending(kind),
    { staleTime: 10 * 60 * 1000 }
  );

export const useScoreboard = () =>
  useQuery<ScoreboardGame[], ApiError>(['news', 'scoreboard'], () => newsService.scoreboard(), {
    // Live scores go stale fast, but only while games are actually running.
    staleTime: 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });

/** On demand, not on load: it costs a model call. */
export const useDigest = (leagueId: number) =>
  useMutation<NewsDigest, ApiError, { publish?: boolean } | void>(
    (opts) => newsService.digest(leagueId, (opts && opts.publish) || false),
    {
      onError: (error) => {
        toast.error(error.detail || "Couldn't build the digest");
      },
    }
  );
