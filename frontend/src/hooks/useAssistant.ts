import { useMutation, useQuery } from 'react-query';
import toast from 'react-hot-toast';

import { ApiError, ChatReply, ChatTurn, WeeklyPrimer } from '@/types';
import { assistantService } from '@/services/assistant';

export const usePromptSuggestions = (leagueId: number, enabled = true) =>
  useQuery<string[], ApiError>(
    ['assistant', leagueId, 'suggestions'],
    () => assistantService.suggestions(leagueId),
    { enabled: enabled && !!leagueId, staleTime: 5 * 60 * 1000 }
  );

export const useCommissionerChat = (leagueId: number) =>
  useMutation<ChatReply, ApiError, { message: string; history: ChatTurn[] }>(
    ({ message, history }) => assistantService.chat(leagueId, message, history),
    {
      onError: (error) => {
        toast.error(error.detail || 'The Commissioner is not answering');
      },
    }
  );

export const useWeeklyPrimer = (leagueId: number, enabled = true) =>
  useQuery<WeeklyPrimer, ApiError>(
    ['assistant', leagueId, 'primer'],
    () => assistantService.primer(leagueId),
    {
      enabled: enabled && !!leagueId,
      staleTime: 10 * 60 * 1000,
      // 400 means no team claimed yet — a state, not a failure worth retrying.
      retry: false,
    }
  );
