import { useQuery } from 'react-query';
import { User, ApiError } from '@/types';
import { authService } from '@/services/auth';
import toast from 'react-hot-toast';

export const useCurrentUser = () => {
  return useQuery<User, ApiError>(
    ['currentUser'],
    () => authService.getCurrentUser(),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      onError: (error: ApiError) => {
        // Only show toast if it's not a 401 (unauthorized) error
        if (error.status !== 401) {
          toast.error(error.detail || 'Failed to fetch user information');
        }
      },
    }
  );
};