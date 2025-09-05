import { useQuery } from 'react-query';
import { leaguesService } from '@/services/leagues';
import { Matchup } from '@/types';

export const useMatchups = (leagueId: number, week?: number) => {
  return useQuery<Matchup[], Error>(
    ['matchups', leagueId, week],
    () => leaguesService.getMatchups(leagueId, week),
    {
      enabled: !!leagueId,
      staleTime: 30 * 1000, // 30 seconds - shorter for live scoring
      refetchInterval: 60 * 1000, // Auto-refetch every 60 seconds during games
      refetchIntervalInBackground: false, // Only refetch when tab is active
    }
  );
};

export const useCurrentMatchup = (leagueId: number, teamId: number, week?: number) => {
  const { data: matchups, isLoading, error } = useMatchups(leagueId, week);
  
  const currentMatchup = matchups?.find(matchup => 
    matchup.home_team_id === teamId || matchup.away_team_id === teamId
  );

  return {
    data: currentMatchup,
    isLoading,
    error,
    opponent: currentMatchup ? {
      teamId: currentMatchup.home_team_id === teamId 
        ? currentMatchup.away_team_id 
        : currentMatchup.home_team_id,
      teamName: currentMatchup.home_team_id === teamId 
        ? currentMatchup.away_team_name 
        : currentMatchup.home_team_name,
      score: currentMatchup.home_team_id === teamId 
        ? currentMatchup.away_score 
        : currentMatchup.home_score,
    } : null,
    myScore: currentMatchup ? (
      currentMatchup.home_team_id === teamId 
        ? currentMatchup.home_score 
        : currentMatchup.away_score
    ) : null,
  };
};