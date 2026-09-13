import React from 'react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AuthProvider, useAuth } from './AuthContext';
import { ThemeProvider, useTheme } from './ThemeContext';

const auth = vi.hoisted(() => ({
  isAuthenticated: vi.fn(() => false),
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock('@/services/auth', () => ({ authService: auth }));
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

const user = { id: 1, email: 'demo@demo.app', full_name: 'Demo Manager' };

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

beforeEach(() => {
  vi.clearAllMocks();
  auth.isAuthenticated.mockReturnValue(false);
});

describe('AuthContext', () => {
  it('starts signed out when there is no token', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it('restores the session from a stored token', async () => {
    auth.isAuthenticated.mockReturnValue(true);
    auth.getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.user).toEqual(user);
  });

  it('clears a token the server rejects', async () => {
    // An expired token must not leave the app in a half-signed-in state.
    auth.isAuthenticated.mockReturnValue(true);
    auth.getCurrentUser.mockRejectedValue({ detail: 'expired' });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(auth.logout).toHaveBeenCalled();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('signs in and keeps the returned user', async () => {
    auth.login.mockResolvedValue({ user, access_token: 'tok' });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login({ email: 'demo@demo.app', password: 'demo1234' });
    });

    expect(result.current.user).toEqual(user);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('rethrows a failed sign-in so the form can react', async () => {
    auth.login.mockRejectedValue({ detail: 'Bad credentials' });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await expect(
      act(async () => {
        await result.current.login({ email: 'a@b.c', password: 'wrong' });
      })
    ).rejects.toBeTruthy();

    expect(result.current.isAuthenticated).toBe(false);
  });

  it('signs out locally and drops the user', async () => {
    auth.isAuthenticated.mockReturnValue(true);
    auth.getCurrentUser.mockResolvedValue(user);

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    act(() => result.current.logout());

    expect(auth.logout).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('refuses to be used outside the provider', () => {
    // Otherwise the failure is a confusing undefined deref deep in a page.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow(/within an AuthProvider/);
    spy.mockRestore();
  });
});

describe('ThemeContext', () => {
  const Probe = () => {
    const { theme, resolvedTheme, setTheme } = useTheme();
    return (
      <div>
        <span data-testid="mode">{theme}</span>
        <span data-testid="resolved">{resolvedTheme}</span>
        <button onClick={() => setTheme('dark')}>go dark</button>
        <button onClick={() => setTheme('system')}>follow system</button>
      </div>
    );
  };

  const show = () => render(<ThemeProvider><Probe /></ThemeProvider>);

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    document.documentElement.classList.remove('dark');
  });

  it('follows the system by default', () => {
    show();
    expect(screen.getByTestId('mode')).toHaveTextContent('system');
  });

  it('resolves to light when the OS prefers light', () => {
    show();
    expect(screen.getByTestId('resolved')).toHaveTextContent('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('puts the dark class on the root when dark is chosen', async () => {
    show();
    await userEvent.click(screen.getByRole('button', { name: 'go dark' }));

    expect(screen.getByTestId('resolved')).toHaveTextContent('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('remembers the choice', async () => {
    show();
    await userEvent.click(screen.getByRole('button', { name: 'go dark' }));
    expect(localStorage.getItem('ffa-theme')).toBe('dark');
  });

  it('restores a stored choice on the next visit', () => {
    localStorage.setItem('ffa-theme', 'dark');
    show();
    expect(screen.getByTestId('mode')).toHaveTextContent('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('ignores a stored value that is not a theme', () => {
    localStorage.setItem('ffa-theme', 'chartreuse');
    show();
    expect(screen.getByTestId('mode')).toHaveTextContent('system');
  });

  it('can go back to following the system', async () => {
    localStorage.setItem('ffa-theme', 'dark');
    show();
    await userEvent.click(screen.getByRole('button', { name: 'follow system' }));

    expect(screen.getByTestId('mode')).toHaveTextContent('system');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
