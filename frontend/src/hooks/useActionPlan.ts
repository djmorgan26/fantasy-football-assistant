import { useQuery } from 'react-query';

import { ActionPlan, ApiError } from '@/types';
import { actionsService } from '@/services/actions';

/**
 * Injury news lands between visits, not during one, so this refetches on focus
 * rather than on a timer: coming back to the tab is when you want to know a
 * starter was ruled out.
 */
export const useActionPlan = (leagueId: number, enabled = true) =>
  useQuery<ActionPlan, ApiError>(
    ['action-plan', leagueId],
    () => actionsService.get(leagueId),
    {
      enabled: enabled && !!leagueId,
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: true,
      retry: false,
    }
  );
