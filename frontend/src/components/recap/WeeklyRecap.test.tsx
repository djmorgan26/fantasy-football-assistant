import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeeklyRecap } from './WeeklyRecap';
import api from '@/services/api';

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
}));

const mockedGet = vi.mocked(api.get);

describe('WeeklyRecap', () => {
  beforeEach(() => {
    mockedGet.mockReset();
  });

  it('fetches and renders the recap for the previous week', async () => {
    mockedGet.mockResolvedValue({ data: { recap: 'What a week of football chaos.' } });

    render(<WeeklyRecap leagueId={1} leagueName="Test League" currentWeek={14} />);

    await waitFor(() =>
      expect(screen.getByText(/What a week of football chaos/)).toBeInTheDocument()
    );
    // currentWeek 14 means the recap defaults to completed week 13.
    expect(mockedGet).toHaveBeenCalledWith('/recap/league/1/week/13');
  });

  it('shows the error state when the API fails', async () => {
    mockedGet.mockRejectedValue({ detail: 'The AI is asleep', status: 503 });

    render(<WeeklyRecap leagueId={1} leagueName="Test League" currentWeek={14} />);

    await waitFor(() =>
      expect(screen.getByText(/The AI is asleep/)).toBeInTheDocument()
    );
  });

  it('navigates between weeks', async () => {
    mockedGet.mockResolvedValue({ data: { recap: 'Recap text' } });
    const user = userEvent.setup();

    render(<WeeklyRecap leagueId={1} leagueName="Test League" currentWeek={14} />);
    await waitFor(() => expect(screen.getByText('Recap text')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /previous/i }));
    await waitFor(() =>
      expect(mockedGet).toHaveBeenCalledWith('/recap/league/1/week/12')
    );
  });
});
