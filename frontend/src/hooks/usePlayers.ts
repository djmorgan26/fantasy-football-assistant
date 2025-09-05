import { useQuery } from 'react-query';
import { PlayerSearchRequest, PlayerSearchResponse, Player, ApiError } from '@/types';
import { playersService } from '@/services/players';
import toast from 'react-hot-toast';

export const useSearchPlayers = (searchRequest: PlayerSearchRequest, enabled: boolean = true) => {
  return useQuery<PlayerSearchResponse, ApiError>(
    ['players', 'search', searchRequest],
    () => playersService.searchPlayers(searchRequest),
    {
      enabled: enabled && !!searchRequest.league_id,
      staleTime: 2 * 60 * 1000, // 2 minutes
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to search players');
      },
    }
  );
};

export const useAvailablePlayers = (
  leagueId: number,
  week?: number,
  position?: string,
  enabled: boolean = true
) => {
  return useQuery<{
    players: Player[];
    total_count: number;
    week?: number;
    position_filter?: string;
  }, ApiError>(
    ['players', 'available', leagueId, week, position],
    () => playersService.getAvailablePlayers(leagueId, week, position),
    {
      enabled: enabled && !!leagueId,
      staleTime: 5 * 60 * 1000, // 5 minutes
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch available players');
      },
    }
  );
};