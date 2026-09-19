import { describe, expect, it, vi, beforeEach } from 'vitest';
import { act, fireEvent } from '@testing-library/react';

import { PullToRefresh } from './PullToRefresh';
import { LiveStatus, describeAge } from './LiveStatus';
import { render, screen } from '@/test/render';

/** jsdom has no scrolling, so the page position is set by hand. */
const scrollTo = (y: number) => {
  Object.defineProperty(window, 'scrollY', { value: y, writable: true });
};

const touch = (y: number) => ({ touches: [{ clientY: y }] });

/** One full gesture. Awaited so the refresh it kicks off settles inside act. */
const pull = async (node: HTMLElement, distance: number) => {
  await act(async () => {
    fireEvent.touchStart(node, touch(0));
    fireEvent.touchMove(node, touch(distance));
    fireEvent.touchEnd(node, { touches: [] });
  });
};

beforeEach(() => scrollTo(0));

describe('PullToRefresh', () => {
  it('refreshes when you pull far enough and let go', async () => {
    const onRefresh = vi.fn(() => Promise.resolve());
    const { container } = render(
      <PullToRefresh onRefresh={onRefresh}>
        <p>Scores</p>
      </PullToRefresh>
    );

    // 400px of finger travel is well past any plausible threshold.
    await pull(container.firstChild as HTMLElement, 400);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('ignores a nudge too small to be meant', async () => {
    // Otherwise every slightly-bouncy scroll costs a round trip.
    const onRefresh = vi.fn(() => Promise.resolve());
    const { container } = render(
      <PullToRefresh onRefresh={onRefresh}>
        <p>Scores</p>
      </PullToRefresh>
    );

    await pull(container.firstChild as HTMLElement, 12);
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('leaves the gesture to the browser when the page is scrolled down', async () => {
    // Pulling mid-page means scrolling up, not refreshing.
    const onRefresh = vi.fn(() => Promise.resolve());
    const { container } = render(
      <PullToRefresh onRefresh={onRefresh}>
        <p>Scores</p>
      </PullToRefresh>
    );

    scrollTo(500);
    await pull(container.firstChild as HTMLElement, 400);
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('does not fire on an upward swipe', async () => {
    const onRefresh = vi.fn(() => Promise.resolve());
    const { container } = render(
      <PullToRefresh onRefresh={onRefresh}>
        <p>Scores</p>
      </PullToRefresh>
    );

    const node = container.firstChild as HTMLElement;
    await act(async () => {
      fireEvent.touchStart(node, touch(300));
      fireEvent.touchMove(node, touch(100));
      fireEvent.touchEnd(node, { touches: [] });
    });
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('can be switched off', async () => {
    const onRefresh = vi.fn(() => Promise.resolve());
    const { container } = render(
      <PullToRefresh onRefresh={onRefresh} disabled>
        <p>Scores</p>
      </PullToRefresh>
    );

    await pull(container.firstChild as HTMLElement, 400);
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('keeps showing its children throughout', () => {
    // The gesture moves the page; it must never replace it.
    const { container } = render(
      <PullToRefresh onRefresh={() => Promise.resolve()} refreshing>
        <p>Scores</p>
      </PullToRefresh>
    );

    expect(screen.getByText('Scores')).toBeInTheDocument();
    expect(container.textContent).toContain('Refreshing');
  });
});

describe('describeAge', () => {
  it('calls a few seconds "just now" rather than counting them', () => {
    expect(describeAge(3 * 1000)).toBe('just now');
  });

  it('counts seconds up to a minute', () => {
    expect(describeAge(34 * 1000)).toBe('34s ago');
  });

  it('switches to minutes', () => {
    expect(describeAge(5 * 60 * 1000)).toBe('5m ago');
  });

  it('switches to hours', () => {
    expect(describeAge(3 * 60 * 60 * 1000)).toBe('3h ago');
  });
});

describe('LiveStatus', () => {
  it('says when the numbers were last fetched', () => {
    render(<LiveStatus updatedAt={Date.now() - 40 * 1000} onRefresh={vi.fn()} />);
    expect(screen.getByText('Updated 40s ago')).toBeInTheDocument();
  });

  it('says it is updating instead of showing a stale age', () => {
    render(<LiveStatus updatedAt={Date.now() - 40 * 1000} refreshing onRefresh={vi.fn()} />);
    expect(screen.getByText('Updating…')).toBeInTheDocument();
    expect(screen.queryByText('Updated 40s ago')).toBeNull();
  });

  it('flags that something is on right now', () => {
    render(<LiveStatus live liveLabel="3 games live" onRefresh={vi.fn()} />);
    expect(screen.getByText('3 games live')).toBeInTheDocument();
  });

  it('will not fire a second refresh while one is running', async () => {
    const onRefresh = vi.fn();
    render(<LiveStatus refreshing onRefresh={onRefresh} />);

    fireEvent.click(screen.getByRole('button', { name: /refresh/i }));
    expect(onRefresh).not.toHaveBeenCalled();
  });
});
