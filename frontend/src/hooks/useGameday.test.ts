import { describe, expect, it } from 'vitest';

import { IDLE_INTERVAL, LIVE_INTERVAL, pollInterval } from './useGameday';

describe('pollInterval', () => {
  it('checks back quickly while a game is being played', () => {
    expect(pollInterval(true)).toBe(LIVE_INTERVAL);
  });

  it('idles when nothing is on', () => {
    // Refetching every thirty seconds on a Tuesday is nobody's battery well spent.
    expect(pollInterval(false)).toBe(IDLE_INTERVAL);
  });

  it('is meaningfully faster when live, not marginally', () => {
    expect(LIVE_INTERVAL * 2).toBeLessThan(IDLE_INTERVAL);
  });
});
