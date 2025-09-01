import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Team, RosterResponse, ApiError } from '@/types';
import { teamsService } from '@/services/teams';
import toast from 'react-hot-toast';

export const useLeagueTeams = (leagueId: number) => {
  return useQuery<Team[], ApiError>(
    ['teams', leagueId],
    () => teamsService.getLeagueTeams(leagueId),
    {
      enabled: !!leagueId,
      staleTime: 2 * 60 * 1000, // 2 minutes
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch teams');
      },
    }
  );
};

export const useTeam = (teamId: number) => {
  return useQuery<Team, ApiError>(
    ['team', teamId],
    () => teamsService.getTeam(teamId),
    {
      enabled: !!teamId,
      staleTime: 2 * 60 * 1000,
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch team');
      },
    }
  );
};

export const useTeamRoster = (teamId: number, week?: number) => {
  return useQuery<RosterResponse, ApiError>(
    ['roster', teamId, week],
    () => teamsService.getTeamRoster(teamId, week),
    {
      enabled: !!teamId,
      staleTime: 1 * 60 * 1000, // 1 minute
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to fetch roster');
      },
    }
  );
};

export const useClaimTeam = () => {
  const queryClient = useQueryClient();
  
  return useMutation<Team, ApiError, number>(
    (teamId: number) => teamsService.claimTeam(teamId),
    {
      onSuccess: (team: Team) => {
        toast.success(`Successfully claimed ${team.name}!`);
        // Invalidate teams queries to refresh the data
        queryClient.invalidateQueries(['teams']);
      },
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to claim team');
      },
    }
  );
};