import { useMutation, useQuery, useQueryClient } from 'react-query';
import { TradeAnalysisRequest, TradeAnalysisResponse, Trade, ApiError } from '@/types';
import { tradesService } from '@/services/trades';
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