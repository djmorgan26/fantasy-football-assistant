import '@testing-library/jest-dom';
import { vi } from 'vitest';

/**
 * Browser APIs jsdom does not implement.
 *
 * Without these, anything built on Headless UI's Dialog — the modal, the
 * mobile nav drawer, the Commissioner panel, the team picker — throws on mount
 * and renders nothing, so a test looks like a missing element rather than a
 * missing polyfill.
 */

// Headless UI's Dialog observes its panel to manage scroll locking.
if (!('ResizeObserver' in globalThis)) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

if (!('IntersectionObserver' in globalThis)) {
  globalThis.IntersectionObserver = class {
    root = null;
    rootMargin = '';
    thresholds = [];
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return [];
    }
  } as unknown as typeof IntersectionObserver;
}

// ThemeContext reads the OS colour-scheme preference on mount.
if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

// jsdom has no layout engine, so scrollIntoView is undefined; the chat panel
// calls it to keep the newest message in view.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}
