import React from 'react';
import { NavLink } from 'react-router-dom';
import { Bars3Icon } from '@heroicons/react/24/outline';
import { cn } from '@/utils';
import { PRIMARY_NAV, leagueNav, isRealLeagueId, NavItem } from './navConfig';

/**
 * Bottom navigation for phones. Inside a league it carries that league's
 * sections; everywhere else it carries the top-level nav. It shows at most
 * four destinations plus a "More" button that opens the full drawer, because
 * five thumb-sized targets is what a 320px screen fits without crowding.
 */
const MAX_ITEMS = 4;

interface MobileTabBarProps {
  leagueId?: string;
  onMore: () => void;
}

const TabLink: React.FC<{ item: NavItem }> = ({ item }) => {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn(
          'flex min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 py-2 text-[0.6875rem] font-semibold transition-colors',
          isActive ? 'text-brand' : 'text-fg-subtle'
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-6 w-6 shrink-0', isActive ? 'text-brand' : 'text-fg-subtle')} />
          <span className="w-full truncate text-center leading-none">{item.label}</span>
        </>
      )}
    </NavLink>
  );
};

export const MobileTabBar: React.FC<MobileTabBarProps> = ({ leagueId, onMore }) => {
  const items = isRealLeagueId(leagueId) ? leagueNav(leagueId) : PRIMARY_NAV;
  const shown = items.slice(0, MAX_ITEMS);

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/95 pb-safe backdrop-blur-md lg:hidden"
    >
      {/* Capped so the row stays a thumb-width cluster on a tablet instead of
          stretching five items across 768px. */}
      <div className="mx-auto flex h-16 max-w-lg items-stretch px-safe">
        {shown.map((item) => (
          <TabLink key={item.to} item={item} />
        ))}
        <button
          type="button"
          onClick={onMore}
          aria-label="Open navigation menu"
          className="flex min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 py-2 text-[0.6875rem] font-semibold text-fg-subtle transition-colors hover:text-fg"
        >
          <Bars3Icon className="h-6 w-6 shrink-0" />
          <span className="leading-none">More</span>
        </button>
      </div>
    </nav>
  );
};
