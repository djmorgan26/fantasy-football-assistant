import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { waitFor } from '@testing-library/react';

import { renderWithProviders, screen } from '@/test/render';

/**
 * The script loader is cached at module scope on purpose (see the component),
 * which means it also leaks between tests. Re-import the module per test so
 * each one starts with an unloaded script rather than inheriting whatever the
 * previous test left resolved or rejected.
 */
const freshButton = async () => {
  vi.resetModules();
  const mod = await import('./GoogleSignInButton');
  return mod.GoogleSignInButton;
};

const getMeta = vi.fn();
const loginWithGoogle = vi.fn();

vi.mock('@/services/meta', () => ({
  metaService: { getMeta: (...args: unknown[]) => getMeta(...args) },
}));

vi.mock('@/contexts/AuthContext', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/AuthContext')>(
    '@/contexts/AuthContext'
  );
  return {
    ...actual,
    useAuth: () => ({ loginWithGoogle }),
  };
});

/** Stand in for Google's script: record the config, expose the callback. */
const installGoogleStub = () => {
  const initialize = vi.fn();
  const renderButton = vi.fn((parent: HTMLElement) => {
    parent.appendChild(document.createElement('div'));
  });
  (window as any).google = { accounts: { id: { initialize, renderButton } } };
  return { initialize, renderButton };
};

/** Resolve whatever <script> the component appended. */
const resolveScript = (outcome: 'load' | 'error' = 'load') => {
  const script = document.querySelector<HTMLScriptElement>(
    'script[src="https://accounts.google.com/gsi/client"]'
  );
  script?.dispatchEvent(new Event(outcome));
  return script;
};

describe('GoogleSignInButton', () => {
  beforeEach(() => {
    getMeta.mockReset();
    loginWithGoogle.mockReset().mockResolvedValue(undefined);
    delete (window as any).google;
    document
      .querySelectorAll('script[src="https://accounts.google.com/gsi/client"]')
      .forEach((s) => s.remove());
  });

  afterEach(() => {
    delete (window as any).google;
  });

  it('renders nothing when the server has no client id configured', async () => {
    // Half-enabled Google sign-in is worse than none: a button that can only
    // fail. The backend leaving GOOGLE_CLIENT_ID empty must hide it entirely.
    getMeta.mockResolvedValue({ mock_mode: false, app_name: 'x', version: '1' });
    const Button = await freshButton();

    renderWithProviders(<Button />);

    await waitFor(() => expect(getMeta).toHaveBeenCalled());
    expect(screen.queryByTestId('google-signin-button')).toBeNull();
  });

  it('renders nothing when the client id is an empty string', async () => {
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: '',
    });
    const Button = await freshButton();

    renderWithProviders(<Button />);

    await waitFor(() => expect(getMeta).toHaveBeenCalled());
    expect(screen.queryByTestId('google-signin-button')).toBeNull();
  });

  it('asks Google to draw the button with the configured client id', async () => {
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: 'abc.apps.googleusercontent.com',
    });
    const google = installGoogleStub();
    const Button = await freshButton();

    renderWithProviders(<Button />);

    await waitFor(() => expect(google.initialize).toHaveBeenCalled());
    expect(google.initialize.mock.calls[0][0]).toMatchObject({
      client_id: 'abc.apps.googleusercontent.com',
    });
    expect(google.renderButton).toHaveBeenCalled();
  });

  it('hands the credential to the auth context and reports success', async () => {
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: 'abc.apps.googleusercontent.com',
    });
    const google = installGoogleStub();
    const onSuccess = vi.fn();
    const Button = await freshButton();

    renderWithProviders(<Button onSuccess={onSuccess} />);

    await waitFor(() => expect(google.initialize).toHaveBeenCalled());

    const { callback } = google.initialize.mock.calls[0][0] as {
      callback: (r: { credential?: string }) => void;
    };
    callback({ credential: 'a-google-id-token' });

    await waitFor(() => expect(loginWithGoogle).toHaveBeenCalledWith('a-google-id-token'));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it('ignores a callback that arrives with no credential', async () => {
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: 'abc.apps.googleusercontent.com',
    });
    const google = installGoogleStub();
    const Button = await freshButton();

    renderWithProviders(<Button />);
    await waitFor(() => expect(google.initialize).toHaveBeenCalled());

    const { callback } = google.initialize.mock.calls[0][0] as {
      callback: (r: { credential?: string }) => void;
    };
    callback({});

    expect(loginWithGoogle).not.toHaveBeenCalled();
  });

  it('falls back to a message when Google cannot be reached', async () => {
    // Offline, blocked by an extension, or Google down. The password form
    // below is still usable, so say so rather than showing a dead control.
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: 'abc.apps.googleusercontent.com',
    });

    const Button = await freshButton();

    renderWithProviders(<Button />);

    await waitFor(() => expect(document.querySelector('script[src*="gsi/client"]')).toBeTruthy());
    resolveScript('error');

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(/unavailable right now/i)
    );
  });

  it('does not survive a failed load as a permanently broken button', async () => {
    // The loader promise is cached at module scope; a rejection has to clear
    // it, or one bad network moment disables Google for the whole session.
    getMeta.mockResolvedValue({
      mock_mode: false,
      app_name: 'x',
      version: '1',
      google_client_id: 'abc.apps.googleusercontent.com',
    });

    const Button = await freshButton();
    const first = renderWithProviders(<Button />);
    await waitFor(() => expect(document.querySelector('script[src*="gsi/client"]')).toBeTruthy());
    resolveScript('error');
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument());
    first.unmount();

    document
      .querySelectorAll('script[src="https://accounts.google.com/gsi/client"]')
      .forEach((s) => s.remove());

    // Same module instance, so a cached rejection would still be cached here.
    // Mounting again has to append a fresh script rather than re-serving the
    // failure. window.google is deliberately still absent so the loader takes
    // the real path instead of short-circuiting.
    renderWithProviders(<Button />);
    await waitFor(() => expect(document.querySelector('script[src*="gsi/client"]')).toBeTruthy());

    const google = installGoogleStub();
    resolveScript('load');

    await waitFor(() => expect(google.initialize).toHaveBeenCalled());
  });
});
