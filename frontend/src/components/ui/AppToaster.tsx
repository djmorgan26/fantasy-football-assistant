import React from 'react';
import { Toaster } from 'react-hot-toast';

interface AppToasterProps {
  position?: 'top-right' | 'top-center';
}

/**
 * Single, token-aware Toaster. Uses Tailwind classes (not hardcoded hex) so
 * toasts respect light/dark themes. Replaces the duplicated inline configs.
 */
export const AppToaster: React.FC<AppToasterProps> = ({ position = 'top-right' }) => {
  return (
    <Toaster
      position={position}
      toastOptions={{
        duration: 4000,
        className:
          '!bg-surface-raised !text-fg !border !border-border !shadow-elevation-3 !rounded-lg !text-sm',
        success: {
          duration: 3000,
          iconTheme: { primary: 'rgb(var(--brand))', secondary: 'rgb(var(--brand-fg))' },
        },
        error: {
          duration: 5000,
          iconTheme: { primary: 'rgb(var(--accent))', secondary: 'rgb(var(--accent-fg))' },
        },
      }}
    />
  );
};
