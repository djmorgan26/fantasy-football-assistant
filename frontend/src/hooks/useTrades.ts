import { useMutation, useQuery, useQueryClient } from 'react-query';
import {
  ApiError,
  CounterResult,
  Trade,
  TradeAnalysisRequest,
  TradeAnalysisResponse,
  TradeEvaluation,
  TradeEvaluationRequest,
  TradeFinderResult,
  TradeMarket,
  TradeOffers,
} from '@/types';
import { tradesService } from '@/services/trades';
import { tradeWorkbenchService } from '@/services/tradeWorkbench';
import toast from 'react-hot-toast';

export const useAnalyzeTrade = () => {
  return useMutation<TradeAnalysisResponse, ApiError, TradeAnalysisRequest>(
    (tradeRequest: TradeAnalysisRequest) => tradesService.analyzeTrade(tradeRequest),
    {
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to analyze trade');
      },
    }
  );
};

export const useCreateTrade = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Trade, ApiError, {
    league_id: number;
    proposing_team_id: number;
    receiving_team_id: number;
    give_players: number[];
    receive_players: number[];
  }>(
    (tradeData) => tradesService.createTrade(tradeData),
    {
      onSuccess: () => {
        toast.success('Trade created successfully!');
        queryClient.invalidateQueries(['trades']);
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to create trade');
      },
    }
  );
};

export const useUserTrades = () => {
  return useQuery<Trade[], ApiError>(
    ['trades'],
    () => tradesService.getUserTrades(),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch trades');
      },
    }
  );
};

export const useTrade = (tradeId: number) => {
  return useQuery<Trade, ApiError>(
    ['trade', tradeId],
    () => tradesService.getTrade(tradeId),
    {
      enabled: !!tradeId,
      staleTime: 2 * 60 * 1000, // 2 minutes
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch trade');
      },
    }
  );
};
// ---------------------------------------------------------------------------
// Trade workbench
// ---------------------------------------------------------------------------

export const useTradeOffers = (leagueId: number) =>
  useQuery<TradeOffers, ApiError>(
    ['trade-offers', leagueId],
    () => tradeWorkbenchService.getOffers(leagueId),
    { enabled: !!leagueId, staleTime: 60 * 1000 }
  );

export const useTradeMarket = (leagueId: number) =>
  useQuery<TradeMarket, ApiError>(
    ['trade-market', leagueId],
    () => tradeWorkbenchService.getMarket(leagueId),
    { enabled: !!leagueId, staleTime: 5 * 60 * 1000 }
  );

/**
 * The finder walks every roster and scores thousands of candidate swaps, so it
 * is deliberately opt-in (`enabled`) rather than firing when the page mounts.
 */
export const useTradeFinder = (leagueId: number, enabled: boolean) =>
  useQuery<TradeFinderResult, ApiError>(
    ['trade-finder', leagueId],
    () => tradeWorkbenchService.findTrades(leagueId),
    { enabled: !!leagueId && enabled, staleTime: 5 * 60 * 1000 }
  );

export const useEvaluateTrade = (leagueId: number) =>
  useMutation<TradeEvaluation, ApiError, TradeEvaluationRequest>(
    (request) => tradeWorkbenchService.evaluate(leagueId, request),
    {
      onError: (error) => {
        toast.error(error.detail || 'Could not evaluate this trade');
      },
    }
  );

export const useConnectSleeperToken = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>(
    (token) => tradeWorkbenchService.connectSleeperToken(leagueId, token),
    {
      onSuccess: () => {
        toast.success('Sleeper connected. Pending offers should appear now.');
        queryClient.invalidateQueries(['trade-offers', leagueId]);
      },
      onError: (error) => {
        toast.error(error.detail || 'Could not save that Sleeper token');
      },
    }
  );
};

export const useDisconnectSleeperToken = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, void>(
    () => tradeWorkbenchService.disconnectSleeperToken(leagueId),
    {
      onSuccess: () => {
        toast.success('Sleeper token removed');
        queryClient.invalidateQueries(['trade-offers', leagueId]);
      },
    }
  );
};

/**
 * Counter-offers. A mutation rather than a query because the user asks for it,
 * which is the behaviour requested: explore on demand, whatever the verdict.
 */
export const useCounterOffers = (leagueId: number) =>
  useMutation<CounterResult, ApiError, TradeEvaluationRequest & { limit?: number }>(
    (request) => tradeWorkbenchService.counters(leagueId, request),
    {
      onError: (error) => {
        toast.error(error.detail || 'Could not work out a counter');
      },
    }
  );
