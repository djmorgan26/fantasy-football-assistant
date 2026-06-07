import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  cn,
  formatPoints,
  formatRecord,
  getWinPercentage,
  getPositionColor,
  getInjuryStatusColor,
  isValidESPNLeagueId,
  extractESPNCookies,
  debounce,
  storage,
  getErrorMessage,
} from './index';

describe('cn', () => {
  it('joins class names and drops falsy values', () => {
    expect(cn('a', false && 'b', 'c')).toBe('a c');
  });
});

describe('formatPoints', () => {
  it('formats to one decimal place', () => {
    expect(formatPoints(123.456)).toBe('123.5');
    expect(formatPoints(0)).toBe('0.0');
  });
});

describe('formatRecord', () => {
  it('omits ties when zero', () => {
    expect(formatRecord(9, 4)).toBe('9-4');
    expect(formatRecord(9, 4, 0)).toBe('9-4');
  });
  it('includes ties when present', () => {
    expect(formatRecord(8, 4, 1)).toBe('8-4-1');
  });
});

describe('getWinPercentage', () => {
  it('handles zero games', () => {
    expect(getWinPercentage(0, 0)).toBe(0);
  });
  it('counts ties as half wins', () => {
    expect(getWinPercentage(1, 1, 2)).toBe(50);
  });
  it('computes basic percentage', () => {
    expect(getWinPercentage(9, 4)).toBeCloseTo(69.23, 1);
  });
});

describe('getPositionColor', () => {
  it('maps known positions', () => {
    expect(getPositionColor('QB')).toContain('red');
    expect(getPositionColor('rb')).toContain('green');
    expect(getPositionColor('D/ST')).toContain('gray');
  });
  it('treats all defense spellings as neutral', () => {
    const neutral = getPositionColor('D/ST');
    expect(getPositionColor('DEF')).toBe(neutral);
    expect(getPositionColor('DST')).toBe(neutral);
  });
  it('falls back to the neutral token for unknown/empty positions', () => {
    expect(getPositionColor('XX')).toContain('surface-sunken');
    expect(getPositionColor('')).toContain('surface-sunken');
  });
});

describe('getInjuryStatusColor', () => {
  it('treats missing/ACTIVE as healthy', () => {
    expect(getInjuryStatusColor()).toContain('green');
    expect(getInjuryStatusColor('ACTIVE')).toContain('green');
  });
  it('maps severity levels', () => {
    expect(getInjuryStatusColor('QUESTIONABLE')).toContain('yellow');
    expect(getInjuryStatusColor('OUT')).toContain('red');
    expect(getInjuryStatusColor('IR')).toContain('red');
  });
});

describe('isValidESPNLeagueId', () => {
  it('accepts positive integers', () => {
    expect(isValidESPNLeagueId('1725275280')).toBe(true);
  });
  it('rejects junk', () => {
    expect(isValidESPNLeagueId('abc')).toBe(false);
    expect(isValidESPNLeagueId('-5')).toBe(false);
    expect(isValidESPNLeagueId('0')).toBe(false);
  });
});

describe('extractESPNCookies', () => {
  it('extracts both cookies from a pasted blob', () => {
    const text = 'espn_s2=ABC123%2F; SWID={XYZ-456}; other=1';
    expect(extractESPNCookies(text)).toEqual({
      espn_s2: 'ABC123%2F',
      swid: '{XYZ-456}',
    });
  });
  it('returns empty object when nothing matches', () => {
    expect(extractESPNCookies('nothing here')).toEqual({});
  });
  it('handles only one cookie present', () => {
    expect(extractESPNCookies('espn_s2=ONLY')).toEqual({ espn_s2: 'ONLY' });
  });
});

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('only fires the trailing call', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 200);
    debounced('a');
    debounced('b');
    debounced('c');
    vi.advanceTimersByTime(250);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith('c');
  });
});

describe('storage', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips JSON values', () => {
    storage.set('key', { a: 1 });
    expect(storage.get('key', null)).toEqual({ a: 1 });
  });
  it('returns default for missing keys', () => {
    expect(storage.get('missing', 'fallback')).toBe('fallback');
  });
  it('returns default for corrupt JSON', () => {
    localStorage.setItem('bad', '{not json');
    expect(storage.get('bad', 'fallback')).toBe('fallback');
  });
  it('removes keys', () => {
    storage.set('gone', 1);
    storage.remove('gone');
    expect(storage.get('gone', 'default')).toBe('default');
  });
});

describe('getErrorMessage', () => {
  it('unwraps Error instances', () => {
    expect(getErrorMessage(new Error('boom'))).toBe('boom');
  });
  it('passes strings through', () => {
    expect(getErrorMessage('plain')).toBe('plain');
  });
  it('falls back for unknown shapes', () => {
    expect(getErrorMessage({ weird: true })).toBe('An unexpected error occurred');
  });
});
