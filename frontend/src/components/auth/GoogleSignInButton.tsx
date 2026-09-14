import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { metaService } from '@/services/meta';

const GSI_SRC = 'https://accounts.google.com/gsi/client';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

/**
 * Loads Google's Identity Services script exactly once per page.
 *
 * Both the login and register forms render this button, and React Router
 * swaps between them without a reload, so a naive per-mount <script> append
 * would stack up copies and re-run the library. The promise is cached at
 * module scope so every caller after the first awaits the same load.
 */
let gsiLoader: Promise<void> | null = null;

const loadGoogleScript = (): Promise<void> => {
  if (gsiLoader) return gsiLoader;

  gsiLoader = new Promise<void>((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SRC}"]`);
    const script = existing ?? document.createElement('script');
    script.addEventListener('load', () => resolve());
    script.addEventListener('error', () => {
      // Let a later mount retry: a network blip on first paint should not
      // disable the button for the rest of the session.
      gsiLoader = null;
      reject(new Error('Could not load Google sign-in'));
    });
    if (!existing) {
      script.src = GSI_SRC;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
  });

  return gsiLoader;
};

interface GoogleSignInButtonProps {
  onSuccess?: () => void;
  /** Google renders its own text; "signup_with" reads better on the register form. */
  text?: 'signin_with' | 'signup_with' | 'continue_with';
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  onSuccess,
  text = 'signin_with',
}) => {
  const { loginWithGoogle } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  // Keep the newest callback in a ref. Google holds onto whatever function we
  // pass to initialize(), and re-running initialize on every render to give it
  // a fresh closure makes it tear down and re-render the button.
  const handleCredential = useRef<(credential: string) => void>(() => {});
  handleCredential.current = (credential: string) => {
    loginWithGoogle(credential)
      .then(() => onSuccess?.())
      .catch(() => {
        /* AuthContext surfaces the error as a toast */
      });
  };

  useEffect(() => {
    let cancelled = false;
    metaService
      .getMeta()
      .then((meta) => {
        if (!cancelled) setClientId(meta.google_client_id || null);
      })
      .catch(() => {
        if (!cancelled) setClientId(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!clientId || !containerRef.current) return;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        const parent = containerRef.current;
        if (cancelled || !parent || !window.google) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response: { credential?: string }) => {
            if (response.credential) handleCredential.current(response.credential);
          },
        });

        // Google draws into a shadow root and will happily stack buttons if
        // this effect runs twice (StrictMode does exactly that in dev).
        parent.innerHTML = '';
        window.google.accounts.id.renderButton(parent, {
          type: 'standard',
          theme: document.documentElement.classList.contains('dark')
            ? 'filled_black'
            : 'outline',
          size: 'large',
          text,
          shape: 'pill',
          logo_alignment: 'left',
          // GIS needs a pixel width and caps it at 400. Matching the real
          // container keeps it flush with the form inputs above it instead of
          // sitting at some arbitrary default width.
          width: Math.min(parent.offsetWidth || 320, 400),
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [clientId, text]);

  // Nothing configured server-side, so there is no button to offer. Render
  // nothing rather than a dead control.
  if (!clientId) return null;

  if (failed) {
    return (
      <p className="text-center text-xs text-fg-muted" role="status">
        Google sign-in is unavailable right now. Use your email and password below.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div ref={containerRef} className="flex justify-center" data-testid="google-signin-button" />
      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-xs uppercase tracking-wide text-fg-subtle">or</span>
        <span className="h-px flex-1 bg-border" />
      </div>
    </div>
  );
};
