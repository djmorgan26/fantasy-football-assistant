import { useQuery, useMutation, useQueryClient } from 'react-query';
import { League, LeagueConnectionRequest, LeagueConnectionResponse, ApiError } from '@/types';
import { leaguesService } from '@/services/leagues';
import { invalidateLeagueIdentity } from './invalidate';
import toast from 'react-hot-toast';

export const useLeagues = () => {
  return useQuery<League[], ApiError>('leagues', leaguesService.getUserLeagues, {
    staleTime: 5 * 60 * 1000, // 5 minutes
    onError: (error: ApiError) => {
      toast.error(error.detail || 'Failed to fetch leagues');
    },
  });
};

export const useLeague = (leagueId: number) => {
  return useQuery<League, ApiError>(
    ['league', leagueId],
    () => leaguesService.getLeague(leagueId),
    {
      enabled: !!leagueId,
      staleTime: 5 * 60 * 1000,
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch league');
      },
    }
  );
};

export const useConnectLeague = () => {
  const queryClient = useQueryClient();
  
  return useMutation<LeagueConnectionResponse, ApiError, LeagueConnectionRequest>(
    leaguesService.connectLeague,
    {
      onSuccess: (data) => {
        if (data.success) {
          toast.success(data.message);
          // Connecting may have added you to a league that already existed, so
          // the whole league view is new to you, not just the list.
          invalidateLeagueIdentity(queryClient, data.league?.id);
        } else {
          toast.error(data.message);
        }
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to connect league');
      },
    }
  );
};

export const useDisconnectLeague = () => {
  const queryClient = useQueryClient();
  
  return useMutation<{ message: string }, ApiError, number>(
    leaguesService.disconnectLeague,
    {
      onSuccess: (data, leagueId) => {
        toast.success(data.message);
        invalidateLeagueIdentity(queryClient, leagueId);
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to disconnect league');
      },
    }
  );
};

export const useSyncLeague = () => {
  const queryClient = useQueryClient();
  
  return useMutation<LeagueConnectionResponse, ApiError, number>(
    leaguesService.syncLeague,
    {
      onSuccess: (data) => {
        if (data.success) {
          toast.success(data.message);
          // A sync rewrites teams, records and rosters, which every league page
          // is downstream of.
          invalidateLeagueIdentity(queryClient, data.league?.id);
        } else {
          toast.error(data.message);
        }
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to sync league data');
      },
    }
  );
};