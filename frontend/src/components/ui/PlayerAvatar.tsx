import React, { useState } from 'react';
import { cn } from '@/utils';

/**
 * A player's face, with initials as the fallback.
 *
 * ESPN serves transparent headshot PNGs cut to the shoulders from a public CDN,
 * keyed by the same player id the roster endpoints already return — so this
 * costs no API work, just a URL. Not every player has one (practice-squad
 * call-ups especially), and team defenses have none at all, so the initials
 * circle stays as the fallback rather than leaving a broken image.
 */
const ESPN_HEADSHOT = 'https://a.espncdn.com/i/headshots/nfl/players/full';

const sizes = {
  sm: 'h-8 w-8 text-[10px]',
  md: 'h-9 w-9 text-xs',
  lg: 'h-11 w-11 text-sm',
} as const;

interface PlayerAvatarProps {
  name: string;
  /** ESPN player id. Absent or unknown falls back to initials. */
  playerId?: number | null;
  /** A ready-made URL (the trending feed supplies one). Wins over playerId. */
  src?: string | null;
  position?: string | null;
  size?: keyof typeof sizes;
  className?: string;
}

const initials = (name: string) =>
  name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

export const PlayerAvatar: React.FC<PlayerAvatarProps> = ({
  name,
  playerId,
  src,
  position,
  size = 'md',
  className,
}) => {
  const [failed, setFailed] = useState(false);

  // Team defenses are a logo, not a face; don't even try the headshot CDN.
  const isTeamDefense = position === 'D/ST' || position === 'DEF';
  const url = src || (playerId && !isTeamDefense ? `${ESPN_HEADSHOT}/${playerId}.png` : null);

  const base = cn(
    'flex shrink-0 items-center justify-center overflow-hidden rounded-full font-bold',
    sizes[size],
    className
  );

  if (!url || failed) {
    return (
      <div
        className={cn(base, 'bg-gradient-to-br from-brand to-primary-700 text-brand-fg')}
        aria-hidden
      >
        {initials(name)}
      </div>
    );
  }

  return (
    <div className={cn(base, 'bg-surface-sunken')}>
      <img
        src={url}
        alt=""
        loading="lazy"
        onError={() => setFailed(true)}
        className="h-full w-full object-cover object-top"
      />
    </div>
  );
};
