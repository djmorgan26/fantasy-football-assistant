import { useState } from 'react';
import { ApiError } from '@/types';
import toast from 'react-hot-toast';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (...args: any[]) => Promise<T>;
  reset: () => void;
}

export const useApi = <T>(
  apiFunction: (...args: any[]) => Promise<T>,
  showSuccessToast = false,
  successMessage = 'Success!'
): UseApiReturn<T> => {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = async (...args: any[]): Promise<T> => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const result = await apiFunction(...args);
      setState({ data: result, loading: false, error: null });
      
      if (showSuccessToast) {
        toast.success(successMessage);
      }
      
      return result;
    } catch (error) {
      const apiError = error as ApiError;
      const errorMessage = apiError.detail || 'An unexpected error occurred';
      
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
      
      toast.error(errorMessage);
      throw error;
    }
  };

  const reset = () => {
    setState({
      data: null,
      loading: false,
      error: null,
    });
  };

  return {
    ...state,
    execute,
    reset,
  };
};

// Hook for form submissions with loading states
export const useFormSubmission = <T>(
  submitFunction: (data: any) => Promise<T>,
  successMessage = 'Success!'
) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (data: any): Promise<T> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const result = await submitFunction(data);
      toast.success(successMessage);
      return result;
    } catch (error) {
      const apiError = error as ApiError;
      const errorMessage = apiError.detail || 'Submission failed';
      setError(errorMessage);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const reset = () => {
    setError(null);
    setIsSubmitting(false);
  };

  return {
    submit,
    isSubmitting,
    error,
    reset,
  };
};