import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { PlayerAvatar } from './PlayerAvatar';

describe('PlayerAvatar', () => {
  it('builds the ESPN headshot URL from the roster player id', () => {
    const { container } = render(<PlayerAvatar name="Josh Allen" playerId={3918298} />);
    expect(container.querySelector('img')).toHaveAttribute(
      'src',
      'https://a.espncdn.com/i/headshots/nfl/players/full/3918298.png'
    );
  });

  it('prefers an explicitly supplied image over the id', () => {
    const { container } = render(
      <PlayerAvatar name="Josh Allen" playerId={3918298} src="https://example.test/a.jpg" />
    );
    expect(container.querySelector('img')).toHaveAttribute('src', 'https://example.test/a.jpg');
  });

  it('falls back to initials when there is no id', () => {
    render(<PlayerAvatar name="Christian McCaffrey" />);
    expect(screen.getByText('CM')).toBeInTheDocument();
  });

  it('does not ask the headshot CDN for a team defense', () => {
    const { container } = render(
      <PlayerAvatar name="49ers D/ST" playerId={123} position="D/ST" />
    );
    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByText('4D')).toBeInTheDocument();
  });

  it('swaps to initials when the image 404s', () => {
    const { container } = render(<PlayerAvatar name="Tank Dell" playerId={4432773} />);
    const img = container.querySelector('img');
    expect(img).not.toBeNull();

    fireEvent.error(img!);

    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByText('TD')).toBeInTheDocument();
  });
});
