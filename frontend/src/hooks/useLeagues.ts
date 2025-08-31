import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { League, LeagueConnectionRequest, LeagueConnectionResponse, ApiError } from '@/types';
import { leaguesService } from '@/services/leagues';
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
          // Invalidate leagues query to refetch the list
          queryClient.invalidateQueries('leagues');
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
      onSuccess: (data) => {
        toast.success(data.message);
        queryClient.invalidateQueries('leagues');
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to disconnect league');
      },
    }
  );
};