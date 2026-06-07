import React from 'react';
import { NavLink } from 'react-router-dom';
import { cn } from '@/utils';
import { PRIMARY_NAV, leagueNav, isRealLeagueId, NavItem } from './navConfig';

const linkClasses = (collapsed: boolean) => ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    collapsed && 'justify-center px-2',
    isActive
      ? 'bg-brand/10 text-brand'
      : 'text-fg-muted hover:bg-surface-sunken hover:text-fg'
  );

const NavRow: React.FC<{ item: NavItem; collapsed?: boolean; onNavigate?: () => void }> = ({
  item,
  collapsed = false,
  onNavigate,
}) => {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={linkClasses(collapsed)}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      aria-label={item.label}
    >
      {({ isActive }) => (
        <>
          <Icon className={cn('h-5 w-5 flex-shrink-0', isActive ? 'text-brand' : 'text-fg-subtle')} />
          {!collapsed && item.label}
        </>
      )}
    </NavLink>
  );
};

interface SidebarNavProps {
  /** Active league id (from the current route), if any. */
  leagueId?: string;
  leagueName?: string;
  /** Icon-only rail mode (desktop sidebar when collapsed). */
  collapsed?: boolean;
  onNavigate?: () => void;
}

/** Shared nav body for the desktop sidebar and the mobile drawer. */
export const SidebarNav: React.FC<SidebarNavProps> = ({
  leagueId,
  leagueName,
  collapsed = false,
  onNavigate,
}) => {
  const showLeague = isRealLeagueId(leagueId);

  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {PRIMARY_NAV.map((item) => (
        <NavRow key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
      ))}

      {showLeague && (
        <div className="mt-6">
          {collapsed ? (
            <div className="mx-2 mb-2 border-t border-border" role="separator" />
          ) : (
            <p className="px-3 pb-2 text-xs font-bold uppercase tracking-wider text-fg-subtle">
              {leagueName || 'This League'}
            </p>
          )}
          <div className="flex flex-col gap-1">
            {leagueNav(leagueId as string).map((item) => (
              <NavRow key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      )}
    </nav>
  );
};
