import {
  HomeIcon,
  TrophyIcon,
  Squares2X2Icon,
  UserGroupIcon,
  MagnifyingGlassIcon,
  ArrowsRightLeftIcon,
  BoltIcon,
  NewspaperIcon,
  ChatBubbleLeftRightIcon,
  RssIcon,
  SignalIcon,
  Square3Stack3DIcon,
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
  // Spans every league rather than living inside one, so it belongs here
  // rather than in the per-league nav.
  { label: 'Across Leagues', to: '/across-leagues', icon: Square3Stack3DIcon },
];

/** Per-league sub-navigation, built from a league id. */
export const leagueNav = (leagueId: string): NavItem[] => [
  { label: 'Overview', to: `/leagues/${leagueId}`, icon: Squares2X2Icon, end: true },
  { label: 'My Roster', to: `/leagues/${leagueId}/roster`, icon: UserGroupIcon },
  // Order is the mobile tab bar's order, and it only shows four. Game Day is
  // the most valuable screen in the app on a Sunday; the board is the reason to
  // open it the rest of the week. The wire is a weekday read and sits behind More.
  { label: 'Game Day', to: `/leagues/${leagueId}/gameday`, icon: SignalIcon },
  { label: 'Board', to: `/leagues/${leagueId}/board`, icon: ChatBubbleLeftRightIcon },
  { label: 'News', to: `/leagues/${leagueId}/news`, icon: RssIcon },
  { label: 'Players', to: `/leagues/${leagueId}/players`, icon: MagnifyingGlassIcon },
  { label: 'Trades', to: `/leagues/${leagueId}/trades`, icon: ArrowsRightLeftIcon },
  { label: 'Draft', to: `/leagues/${leagueId}/draft`, icon: BoltIcon },
  { label: 'Press Box', to: `/leagues/${leagueId}/press-box`, icon: NewspaperIcon },
];

/** A route param of "connect"/"sleeper" is a flow, not a real league. */
export const isRealLeagueId = (id?: string): id is string =>
  !!id && id !== 'connect' && id !== 'sleeper';
