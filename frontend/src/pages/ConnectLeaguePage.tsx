import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { CheckCircleIcon } from '@heroicons/react/24/solid';

import { EspnConnectForm } from '@/components/connect/EspnConnectForm';
import { SleeperConnectForm } from '@/components/connect/SleeperConnectForm';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/utils';

/**
 * Connect a league from either platform.
 *
 * Both platforms live on one screen rather than behind separate routes: the
 * Dashboard's Connect League button used to land straight on the ESPN form, so
 * a Sleeper league looked unsupported unless you happened to find the second
 * link on the Leagues page. Picking is now the first thing the page asks, and
 * switching is one tap rather than a trip back.
 */
type Platform = 'espn' | 'sleeper' | 'yahoo';

const PLATFORMS: {
  key: Platform;
  name: string;
  monogram: string;
  needs: string;
  mark: string;
  ring: string;
  /** Selectable platforms only. See the Yahoo entry for why it is not. */
  comingSoon?: boolean;
}[] = [
  {
    key: 'espn',
    name: 'ESPN',
    monogram: 'E',
    needs: 'Needs your league ID, or just paste the league link',
    mark: 'bg-[#cc0000] text-white',
    ring: 'border-[#cc0000] bg-[#cc0000]/5',
  },
  {
    key: 'sleeper',
    name: 'Sleeper',
    monogram: 'S',
    needs: 'Needs only your username, no password',
    mark: 'bg-[#4f46e5] text-white',
    ring: 'border-[#4f46e5] bg-[#4f46e5]/5',
  },
  {
    // Not selectable on purpose. The OAuth flow and league discovery are
    // written, but Yahoo issues Fantasy API credentials only to a developer
    // app they have reviewed and approved, and that approval has not come
    // through. Until it does, a connected Yahoo league would load with no
    // roster, no matchups and no waiver budget, which reads as a broken app
    // rather than an unfinished integration. Offering it and failing is worse
    // than saying plainly that it is not ready.
    key: 'yahoo',
    name: 'Yahoo',
    monogram: 'Y!',
    needs: 'Waiting on Yahoo to approve our API access',
    mark: 'bg-[#6001d2] text-white',
    ring: 'border-[#6001d2] bg-[#6001d2]/5',
    comingSoon: true,
  },
];

export const ConnectLeaguePage: React.FC = () => {
  const { pathname } = useLocation();
  // Nothing links to /leagues/sleeper/connect any more, but the route is kept
  // so an old bookmark still works, and it lands on Sleeper as it used to.
  const [platform, setPlatform] = useState<Platform>(() => {
    // ?platform=yahoo used to select Yahoo. It now falls through to ESPN
    // rather than landing on a card that cannot be used.
    return pathname.includes('sleeper') ? 'sleeper' : 'espn';
  });

  return (
    <PageContainer width="narrow">
      <PageHeader
        title="Connect a league"
        subtitle="Works with ESPN and Sleeper. Connect as many as you like."
      />

      <fieldset className="mb-6">
        <legend className="mb-2 text-sm font-medium text-fg">Where is your league?</legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PLATFORMS.map((option) => {
            const active = platform === option.key && !option.comingSoon;
            return (
              <button
                key={option.key}
                type="button"
                aria-pressed={active}
                disabled={option.comingSoon}
                title={option.comingSoon ? 'Not available yet' : undefined}
                onClick={() => !option.comingSoon && setPlatform(option.key)}
                className={cn(
                  'relative flex items-center gap-3 rounded-card border-2 p-4 text-left transition-colors',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  option.comingSoon
                    ? 'cursor-not-allowed border-border bg-surface-sunken opacity-60'
                    : active
                    ? option.ring
                    : 'border-border bg-surface-raised hover:border-border-strong hover:bg-surface-sunken'
                )}
              >
                <span
                  className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg font-display text-lg font-bold',
                    option.mark
                  )}
                  aria-hidden="true"
                >
                  {option.monogram}
                </span>
                <span className="min-w-0">
                  <span className="flex items-center gap-2">
                    <span className="font-semibold text-fg">{option.name}</span>
                    {option.comingSoon && (
                      <Badge variant="default" size="sm">
                        Coming soon
                      </Badge>
                    )}
                  </span>
                  <span className="block text-xs text-fg-muted">{option.needs}</span>
                </span>
                {active && (
                  <CheckCircleIcon className="absolute right-3 top-3 h-5 w-5 text-brand" />
                )}
              </button>
            );
          })}
        </div>
      </fieldset>

      <Card>
        <CardContent className="p-4 sm:p-6">
          {/* Keyed so switching platforms resets the other form's state rather
              than leaving a half-filled field behind it. */}
            {platform === 'sleeper' ? (
              <SleeperConnectForm key="sleeper" />
            ) : (
              <EspnConnectForm key="espn" />
            )}
        </CardContent>
      </Card>

      <p className="mt-6 text-center text-xs text-fg-subtle">
        We are not affiliated with ESPN, Sleeper, or Yahoo. Platform names identify league
        connections only.
      </p>
    </PageContainer>
  );
};
