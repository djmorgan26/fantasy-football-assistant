import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider, setLogger } from 'react-query';

/**
 * Render a component with the providers it would have in the real app.
 *
 * Retries and error logging are off: a test that asserts on a failure state
 * should reach it immediately, and react-query's console noise otherwise
 * drowns the actual assertion output.
 */
export const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      // No retries: a test asserting on a failure state should reach it at
      // once. cacheTime is left alone — zeroing it garbage-collects anything
      // seeded with setQueryData before a component subscribes to it.
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

// react-query logs every failed query to the console. In a suite that asserts
// on failure states that is pure noise drowning the real output. v3 takes this
// globally rather than per-client.
setLogger({ log: () => {}, warn: () => {}, error: () => {} });

interface Options extends Omit<RenderOptions, 'wrapper'> {
  /** Initial history entry, for components that read route params. */
  route?: string;
  queryClient?: QueryClient;
}

export function renderWithProviders(ui: ReactElement, options: Options = {}) {
  const { route = '/', queryClient = makeQueryClient(), ...rest } = options;

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...rest }) };
}

export * from '@testing-library/react';
