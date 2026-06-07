import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/utils';
import { PRIMARY_NAV, leagueNav, isRealLeagueId, NavItem } from './navConfig';

const linkClasses = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    isActive
      ? 'bg-brand/10 text-brand'
      : 'text-fg-muted hover:bg-surface-sunken hover:text-fg'
  );

const NavRow: React.FC<{ item: NavItem; onNavigate?: () => void }> = ({ item, onNavigate }) => {
  const Icon = item.icon;
  return (
    <NavLink to={item.to} end={item.end} className={linkClasses} onClick={onNavigate}>
      {({ isActive }) => (
        <>
          <Icon className={cn('h-5 w-5 flex-shrink-0', isActive ? 'text-brand' : 'text-fg-subtle')} />
          {item.label}
        </>
      )}
    </NavLink>
  );
};

interface SidebarNavProps {
  /** Active league id (from the current route), if any. */
  leagueId?: string;
  leagueName?: string;
  onNavigate?: () => void;
}

/** Shared nav body for the desktop sidebar and the mobile drawer. */
export const SidebarNav: React.FC<SidebarNavProps> = ({ leagueId, leagueName, onNavigate }) => {
  const showLeague = isRealLeagueId(leagueId);

  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {PRIMARY_NAV.map((item) => (
        <NavRow key={item.to} item={item} onNavigate={onNavigate} />
      ))}

      {showLeague && (
        <div className="mt-6">
          <p className="px-3 pb-2 text-xs font-bold uppercase tracking-wider text-fg-subtle">
            {leagueName || 'This League'}
          </p>
          <div className="flex flex-col gap-1">
            {leagueNav(leagueId as string).map((item) => (
              <NavRow key={item.to} item={item} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};
