import { describe, expect, it } from 'vitest';

import { PRIMARY_NAV, isRealLeagueId, leagueNav } from './navConfig';

describe('isRealLeagueId', () => {
  it('accepts a numeric id', () => {
    expect(isRealLeagueId('42')).toBe(true);
  });

  it.each(['connect', 'sleeper'])(
    'rejects %s, which is a flow rather than a league',
    (segment) => {
      // /leagues/connect and /leagues/sleeper/connect share the :leagueId slot;
      // treating them as leagues would render league nav on a setup page.
      expect(isRealLeagueId(segment)).toBe(false);
    }
  );

  it.each([undefined, ''])('rejects %s', (value) => {
    expect(isRealLeagueId(value)).toBe(false);
  });
});

describe('leagueNav', () => {
  it('builds every destination under the given league', () => {
    const items = leagueNav('42');
    expect(items.length).toBeGreaterThan(0);
    items.forEach((item) => expect(item.to.startsWith('/leagues/42')).toBe(true));
  });

  it('matches Overview only on the exact path', () => {
    // Without `end`, Overview would stay highlighted on every sub-route.
    const overview = leagueNav('42').find((i) => i.label === 'Overview');
    expect(overview?.end).toBe(true);
    expect(overview?.to).toBe('/leagues/42');
  });

  it('spends the tab bar\'s four slots on the screens people open', () => {
    // MobileTabBar slices the first four. Game Day is the reason to open the
    // app on a Sunday and the Board is the reason the rest of the week; the
    // wire is a weekday read and deliberately sits behind More.
    const firstFour = leagueNav('42').slice(0, 4).map((i) => i.label);
    expect(firstFour).toEqual(['Overview', 'My Roster', 'Game Day', 'Board']);
    expect(leagueNav('42').map((i) => i.label)).toContain('News');
  });

  it('gives every item an icon and a unique route', () => {
    const items = leagueNav('42');
    items.forEach((item) => expect(item.icon).toBeTruthy());
    expect(new Set(items.map((i) => i.to)).size).toBe(items.length);
  });
});

describe('PRIMARY_NAV', () => {
  it('covers the top level and nothing league-scoped', () => {
    expect(PRIMARY_NAV.map((i) => i.to)).toEqual(['/dashboard', '/leagues']);
  });
});
