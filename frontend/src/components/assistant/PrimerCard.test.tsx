import { describe, expect, it, vi, beforeEach } from 'vitest';

import { PrimerCard } from './PrimerCard';
import { renderWithProviders, screen } from '@/test/render';
import { WeeklyPrimer } from '@/types';

const hookState = vi.hoisted(() => ({
  value: { data: undefined, isLoading: false, isError: false } as {
    data?: WeeklyPrimer;
    isLoading: boolean;
    isError: boolean;
  },
}));

vi.mock('@/hooks/useAssistant', () => ({
  useWeeklyPrimer: () => hookState.value,
}));

const primer = (over: Partial<WeeklyPrimer> = {}): WeeklyPrimer => ({
  week: 14,
  team_name: 'Game of Throws',
  record: '9-4',
  opponent: 'Comeback Cats',
  projected: 167.6,
  starters: 9,
  alerts: [],
  best_swap: null,
  trash_talk: null,
  ...over,
});

const show = (p?: WeeklyPrimer, flags: Partial<typeof hookState.value> = {}) => {
  hookState.value = { data: p, isLoading: false, isError: !p, ...flags };
  return renderWithProviders(<PrimerCard leagueId={1} />);
};

beforeEach(() => {
  hookState.value = { data: undefined, isLoading: false, isError: false };
});

describe('PrimerCard', () => {
  it('leads with the week, the team and the projection', () => {
    show(primer());
    expect(screen.getByText('Your Week 14')).toBeInTheDocument();
    expect(screen.getByText(/Game of Throws/)).toBeInTheDocument();
    expect(screen.getByText('167.6')).toBeInTheDocument();
  });

  it('names this week’s opponent', () => {
    show(primer());
    expect(screen.getByText('Comeback Cats')).toBeInTheDocument();
  });

  it('says so when there is no opponent', () => {
    show(primer({ opponent: null }));
    expect(screen.getByText('No opponent')).toBeInTheDocument();
  });

  it('spells out the swap worth making', () => {
    show(primer({
      best_swap: { start: 'Reggie Petrov', sit: 'CeeDee Lamb', slot: 'WR', gain: 7.5 },
    }));

    expect(screen.getByText('Reggie Petrov')).toBeInTheDocument();
    expect(screen.getByText('CeeDee Lamb')).toBeInTheDocument();
    expect(screen.getByText('+7.5')).toBeInTheDocument();
  });

  it('stays quiet when the lineup is already optimal', () => {
    show(primer({ best_swap: null }));
    expect(screen.queryByText(/projected\./)).toBeNull();
  });

  it('counts injured starters in the singular and the plural', () => {
    const alert = { player: 'A.J. Brown', slot: 'WR', status: 'OUT', severity: 'out' as const };

    const { unmount } = show(primer({ alerts: [alert] }));
    expect(screen.getByText('1 starter needs attention')).toBeInTheDocument();
    unmount();

    show(primer({
      alerts: [alert, { ...alert, player: 'Tank Dell', severity: 'questionable' }],
    }));
    expect(screen.getByText('2 starters need attention')).toBeInTheDocument();
  });

  it('hides the alert block when nobody is hurt', () => {
    show(primer());
    expect(screen.queryByText(/needs attention/)).toBeNull();
  });

  it('offers the trash talk for the group chat', () => {
    show(primer({ trash_talk: 'Enjoy the loss.' }));
    expect(screen.getByText(/Enjoy the loss\./)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Copy for the group chat/ })
    ).toBeInTheDocument();
  });

  it('reads fine without the generated flourish', () => {
    // The card is computed; the trash talk is decoration and often absent.
    show(primer({ trash_talk: null }));
    expect(screen.queryByRole('button', { name: /Copy for the group chat/ })).toBeNull();
    expect(screen.getByText('167.6')).toBeInTheDocument();
  });

  it('renders nothing when no team is claimed', () => {
    // The league page already prompts for that; a second empty card is noise.
    const { container } = show(undefined);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows a placeholder while loading', () => {
    hookState.value = { data: undefined, isLoading: true, isError: false };
    const { container } = renderWithProviders(<PrimerCard leagueId={1} />);
    expect(container).not.toBeEmptyDOMElement();
  });
});
