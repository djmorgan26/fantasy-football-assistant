import { useQuery, useMutation } from 'react-query';
import { ValueBoardResponse, DraftAssistResponse, ApiError } from '@/types';
import { draftService } from '@/services/draft';
import toast from 'react-hot-toast';

/** Pre-draft value board for a league (scoring-aware VBD rankings). */
export const useLeagueValueBoard = (leagueId: number, limit = 200, enabled = true) => {
  return useQuery<ValueBoardResponse, ApiError>(
    ['draft', 'value-board', leagueId, limit],
    () => draftService.getLeagueValueBoard(leagueId, limit),
    {
      enabled: enabled && !!leagueId,
      staleTime: 30 * 60 * 1000, // projections are static; cache aggressively
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to load draft board');
      },
    }
  );
};

/**
 * Live draft assistant. When `live` is true it polls every few seconds so the
 * board tracks picks as they happen. AI advice is intentionally excluded here
 * (it is slow) — use useDraftAdvice for that on demand.
 */
export const useDraftAssist = (
  leagueId: number,
  live: boolean,
  limit = 12,
  enabled = true
) => {
  return useQuery<DraftAssistResponse, ApiError>(
    ['draft', 'assist', leagueId, limit],
    () => draftService.getDraftAssist(leagueId, false, limit),
    {
      enabled: enabled && !!leagueId,
      refetchInterval: live ? 8000 : false,
      refetchOnWindowFocus: live,
      // Don't spam toasts on every failed poll; the UI surfaces the error state.
      onError: () => undefined,
    }
  );
};

/** On-demand AI pick advice (runs the LLM; call from a button, not a poll). */
export const useDraftAdvice = (leagueId: number, limit = 12) => {
  return useMutation<DraftAssistResponse, ApiError, void>(
    () => draftService.getDraftAssist(leagueId, true, limit),
    {
      onError: (error: ApiError) => {
        toast.error(error.detail || 'Failed to get AI advice');
      },
    }
  );
};
