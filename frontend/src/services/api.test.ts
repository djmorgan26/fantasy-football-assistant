import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import api, { setAuthToken, removeAuthToken, getAuthToken } from './api';

describe('auth token management', () => {
  beforeEach(() => {
    localStorage.clear();
    removeAuthToken();
  });

  it('setAuthToken persists token and sets default header', () => {
    setAuthToken('tok-123');
    expect(localStorage.getItem('access_token')).toBe('tok-123');
    expect(api.defaults.headers.common['Authorization']).toBe('Bearer tok-123');
    expect(getAuthToken()).toBe('tok-123');
  });

  it('removeAuthToken clears both', () => {
    setAuthToken('tok-123');
    removeAuthToken();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(api.defaults.headers.common['Authorization']).toBeUndefined();
  });
});

describe('response interceptor', () => {
  const realLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    // jsdom cannot navigate; stub location so the 401 redirect is observable.
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...realLocation, pathname: '/dashboard', href: 'http://localhost/dashboard' },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: realLocation,
    });
    vi.restoreAllMocks();
  });

  function adapterRespondingWith(status: number, data: unknown) {
    return vi.fn(async (config: any) => {
      if (status >= 400) {
        const error: any = new Error(`Request failed with status code ${status}`);
        error.config = config;
        error.response = { status, data, headers: {}, config };
        error.isAxiosError = true;
        throw error;
      }
      return { data, status, statusText: 'OK', headers: {}, config };
    });
  }

  it('transforms API errors into {detail, status}', async () => {
    api.defaults.adapter = adapterRespondingWith(404, { detail: 'League not found' });
    await expect(api.get('/leagues/999')).rejects.toEqual({
      detail: 'League not found',
      status: 404,
    });
  });

  it('falls back to the axios message when no detail is present', async () => {
    api.defaults.adapter = adapterRespondingWith(500, {});
    await expect(api.get('/boom')).rejects.toMatchObject({ status: 500 });
  });

  it('on 401 it clears the token and redirects to login', async () => {
    setAuthToken('expired-token');
    api.defaults.adapter = adapterRespondingWith(401, { detail: 'Could not validate credentials' });

    await expect(api.get('/auth/me')).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('does not redirect when already on /login', async () => {
    window.location.pathname = '/login';
    window.location.href = 'http://localhost/login';
    api.defaults.adapter = adapterRespondingWith(401, {});

    await expect(api.post('/auth/login', {})).rejects.toMatchObject({ status: 401 });
    expect(window.location.href).toBe('http://localhost/login');
  });
});
