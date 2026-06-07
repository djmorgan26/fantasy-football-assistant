import {
  HomeIcon,
  TrophyIcon,
  Squares2X2Icon,
  UserGroupIcon,
  MagnifyingGlassIcon,
  ArrowsRightLeftIcon,
  BoltIcon,
  NewspaperIcon,
} from '@heroicons/react/24/outline';

export interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  /** Match only on exact path (for index routes). */
  end?: boolean;
}

/** Top-level navigation. */
export const PRIMARY_NAV: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: HomeIcon },
  { label: 'Leagues', to: '/leagues', icon: TrophyIcon },
];

/** Per-league sub-navigation, built from a league id. */
export const leagueNav = (leagueId: string): NavItem[] => [
  { label: 'Overview', to: `/leagues/${leagueId}`, icon: Squares2X2Icon, end: true },
  { label: 'My Roster', to: `/leagues/${leagueId}/roster`, icon: UserGroupIcon },
  { label: 'Players', to: `/leagues/${leagueId}/players`, icon: MagnifyingGlassIcon },
  { label: 'Trades', to: `/leagues/${leagueId}/trades`, icon: ArrowsRightLeftIcon },
  { label: 'Draft', to: `/leagues/${leagueId}/draft`, icon: BoltIcon },
  { label: 'Press Box', to: `/leagues/${leagueId}/press-box`, icon: NewspaperIcon },
];

/** A route param of "connect"/"sleeper" is a flow, not a real league. */
export const isRealLeagueId = (id?: string): id is string =>
  !!id && id !== 'connect' && id !== 'sleeper';
