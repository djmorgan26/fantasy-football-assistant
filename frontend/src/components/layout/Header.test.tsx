import { describe, expect, it, vi, beforeEach } from 'vitest';

import { Header } from './Header';
import { renderWithProviders, screen } from '@/test/render';

const auth = vi.hoisted(() => ({
  user: { id: 1, email: 'demo@demo.app', full_name: 'Demo Manager' } as
    | { id: number; email: string; full_name: string }
    | null,
  isAuthenticated: true,
  isLoading: false,
  logout: vi.fn(),
}));

vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', resolved: 'light', setTheme: vi.fn() }),
}));

beforeEach(() => {
  auth.user = { id: 1, email: 'demo@demo.app', full_name: 'Demo Manager' };
  auth.isAuthenticated = true;
  auth.isLoading = false;
});

describe('Header', () => {
  it('names the signed-in user', () => {
    renderWithProviders(<Header />);
    expect(screen.getByText('Demo Manager')).toBeInTheDocument();
  });

  it('offers sign in to somebody who is signed out', () => {
    auth.isAuthenticated = false;
    auth.user = null;
    renderWithProviders(<Header />);
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('commits to neither while the session check is still in flight', () => {
    // The check is a round trip. Offering "Sign In" in the meantime told a
    // signed-in user they were signed out, for as long as the request took.
    auth.isLoading = true;
    auth.isAuthenticated = false;
    auth.user = null;
    renderWithProviders(<Header />);

    expect(screen.queryByRole('button', { name: 'Sign In' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Sign Up' })).toBeNull();
    expect(screen.getByRole('status', { name: 'Checking your session' })).toBeInTheDocument();
  });
});
