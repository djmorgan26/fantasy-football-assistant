import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { CommissionerDock } from './CommissionerDock';
import { renderWithProviders, screen, waitFor } from '@/test/render';

const chat = vi.hoisted(() => ({ mutate: vi.fn(), isLoading: false }));
const suggestions = vi.hoisted(() => ({ value: ['Should I start Reggie Petrov?'] }));

vi.mock('@/hooks/useAssistant', () => ({
  useCommissionerChat: () => chat,
  usePromptSuggestions: () => ({ data: suggestions.value }),
}));

beforeEach(() => {
  chat.mutate = vi.fn();
  chat.isLoading = false;
  suggestions.value = ['Should I start Reggie Petrov?'];
});

const open = async (route = '/leagues/42/roster') => {
  const result = renderWithProviders(<CommissionerDock />, { route });
  await userEvent.click(screen.getByRole('button', { name: 'Ask the Commissioner' }));
  // Headless UI mounts the panel through a transition, so it is not in the
  // DOM on the tick the click returns.
  await screen.findByLabelText('Your question');
  return result;
};

describe('CommissionerDock', () => {
  it('offers itself on a league page', () => {
    renderWithProviders(<CommissionerDock />, { route: '/leagues/42/roster' });
    expect(screen.getByRole('button', { name: 'Ask the Commissioner' })).toBeInTheDocument();
  });

  it('offers itself on the league overview too', () => {
    renderWithProviders(<CommissionerDock />, { route: '/leagues/42' });
    expect(screen.getByRole('button', { name: 'Ask the Commissioner' })).toBeInTheDocument();
  });

  it('stays away where there is no league to talk about', () => {
    // It has nothing to be grounded on outside a league.
    const { container } = renderWithProviders(<CommissionerDock />, { route: '/dashboard' });
    expect(container).toBeEmptyDOMElement();
  });

  it('stays away during the connect flow', () => {
    const { container } = renderWithProviders(<CommissionerDock />, {
      route: '/leagues/connect',
    });
    expect(container).toBeEmptyDOMElement();
  });

  it('opens a panel that says what it knows', async () => {
    await open();
    expect(screen.getByRole('heading', { name: 'The Commissioner' })).toBeInTheDocument();
    expect(screen.getByText(/Knows your whole league/)).toBeInTheDocument();
  });

  it('shows prompt chips built from real league state', async () => {
    await open();
    expect(
      screen.getByRole('button', { name: 'Should I start Reggie Petrov?' })
    ).toBeInTheDocument();
  });

  it('asks the chip question when one is tapped', async () => {
    await open();
    await userEvent.click(screen.getByRole('button', { name: 'Should I start Reggie Petrov?' }));

    expect(chat.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Should I start Reggie Petrov?' }),
      expect.anything()
    );
  });

  it('sends a typed question and echoes it immediately', async () => {
    await open();

    await userEvent.type(screen.getByLabelText('Your question'), 'Why did I lose?');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(chat.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Why did I lose?' }),
      expect.anything()
    );
    // The question appears without waiting for the model to answer.
    await waitFor(() => expect(screen.getByText('Why did I lose?')).toBeInTheDocument());
  });

  it('clears the box after sending', async () => {
    await open();
    const box = screen.getByLabelText('Your question');

    await userEvent.type(box, 'Why did I lose?');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));

    await waitFor(() => expect(box).toHaveValue(''));
  });

  it('will not send an empty question', async () => {
    await open();
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(chat.mutate).not.toHaveBeenCalled();
  });

  it('will not send whitespace', async () => {
    await open();
    await userEvent.type(screen.getByLabelText('Your question'), '   ');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(chat.mutate).not.toHaveBeenCalled();
  });

  it('renders the answer when it arrives', async () => {
    chat.mutate = vi.fn((_vars, opts) => opts.onSuccess({ reply: 'Start Petrov.' }));
    await open();

    await userEvent.click(screen.getByRole('button', { name: 'Should I start Reggie Petrov?' }));
    await waitFor(() => expect(screen.getByText('Start Petrov.')).toBeInTheDocument());
  });

  it('says something human when the model fails', async () => {
    chat.mutate = vi.fn((_vars, opts) => opts.onError(new Error('nope')));
    await open();

    await userEvent.click(screen.getByRole('button', { name: 'Should I start Reggie Petrov?' }));
    await waitFor(() =>
      expect(screen.getByText(/couldn't get to that one/i)).toBeInTheDocument()
    );
  });

  it('blocks a second send while one is in flight', async () => {
    chat.isLoading = true;
    await open();

    await userEvent.type(screen.getByLabelText('Your question'), 'Again?');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  });
});
