import { useQuery } from 'react-query';
import { leaguesService } from '@/services/leagues';
import { TeamBudgetSummary } from '@/types';

export const useWaiverBudgets = (leagueId: number) => {
  return useQuery<TeamBudgetSummary[], Error>(
    ['waiver-budgets', leagueId],
    () => leaguesService.getWaiverBudgets(leagueId),
    {
      enabled: !!leagueId,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useTeamBudget = (leagueId: number, teamId: number) => {
  const { data: budgets, isLoading, error } = useWaiverBudgets(leagueId);
  
  const teamBudget = budgets?.find(budget => budget.team_id === teamId);

  return {
    data: teamBudget,
    isLoading,
    error,
    budgetInfo: teamBudget ? {
      remaining: teamBudget.current_budget,
      spent: teamBudget.spent_budget,
      total: teamBudget.total_budget,
      spentPercentage: Math.round((teamBudget.spent_budget / teamBudget.total_budget) * 100),
      remainingPercentage: Math.round((teamBudget.current_budget / teamBudget.total_budget) * 100),
    } : null,
  };
};