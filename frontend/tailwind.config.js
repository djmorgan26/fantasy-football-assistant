/** @type {import('tailwindcss').Config} */
const withAlpha = (v) => `rgb(var(${v}) / <alpha-value>)`;

export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Semantic, theme-aware tokens (flip with .dark)
        surface: {
          DEFAULT: withAlpha('--surface'),
          raised: withAlpha('--surface-raised'),
          sunken: withAlpha('--surface-sunken'),
        },
        border: {
          DEFAULT: withAlpha('--border'),
          strong: withAlpha('--border-strong'),
        },
        fg: {
          DEFAULT: withAlpha('--fg'),
          muted: withAlpha('--fg-muted'),
          subtle: withAlpha('--fg-subtle'),
          inverse: withAlpha('--fg-inverse'),
        },
        brand: {
          DEFAULT: withAlpha('--brand'),
          fg: withAlpha('--brand-fg'),
        },
        accent: {
          DEFAULT: withAlpha('--accent'),
          fg: withAlpha('--accent-fg'),
        },
        ring: withAlpha('--ring'),

        // Brand ramp (field green) — keeps existing primary-* utilities working
        primary: {
          50: '#ecf7f0',
          100: '#d2ecdb',
          200: '#a7d8ba',
          300: '#74bf93',
          400: '#43a06d',
          500: '#22834f',
          600: '#1b7a3d',
          700: '#166233',
          800: '#144e2b',
          900: '#103f24',
        },
        success: {
          50: '#f0fdf4', 100: '#dcfce7', 200: '#bbf7d0', 300: '#86efac', 400: '#4ade80',
          500: '#22c55e', 600: '#16a34a', 700: '#15803d', 800: '#166534', 900: '#14532d',
        },
        warning: {
          50: '#fffbeb', 100: '#fef3c7', 200: '#fde68a', 300: '#fcd34d', 400: '#fbbf24',
          500: '#f59e0b', 600: '#d97706', 700: '#b45309', 800: '#92400e', 900: '#78350f',
        },
        error: {
          50: '#fef2f2', 100: '#fee2e2', 200: '#fecaca', 300: '#fca5a5', 400: '#f87171',
          500: '#ef4444', 600: '#dc2626', 700: '#b91c1c', 800: '#991b1b', 900: '#7f1d1d',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        display: ['Bricolage Grotesque', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-lg': ['2.75rem', { lineHeight: '1.04', letterSpacing: '-0.02em', fontWeight: '800' }],
        'display': ['2.125rem', { lineHeight: '1.08', letterSpacing: '-0.02em', fontWeight: '800' }],
        'display-sm': ['1.625rem', { lineHeight: '1.12', letterSpacing: '-0.01em', fontWeight: '700' }],
      },
      borderRadius: {
        card: '0.875rem',  // 14px — standard card rounding
        pill: '9999px',
      },
      boxShadow: {
        'elevation-1': '0 1px 2px rgba(20, 40, 28, 0.06), 0 1px 1px rgba(20, 40, 28, 0.04)',
        'elevation-2': '0 4px 16px rgba(20, 40, 28, 0.06), 0 1px 3px rgba(20, 40, 28, 0.05)',
        'elevation-3': '0 12px 32px rgba(20, 40, 28, 0.10), 0 4px 8px rgba(20, 40, 28, 0.06)',
        'elevation-4': '0 24px 56px rgba(20, 40, 28, 0.16), 0 8px 16px rgba(20, 40, 28, 0.08)',
        'glow-brand': '0 0 16px rgb(var(--brand) / 0.35)',
        'glow-accent': '0 0 16px rgb(var(--accent) / 0.40)',
      },
    },
  },
  plugins: [],
}
