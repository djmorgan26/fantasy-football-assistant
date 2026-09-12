import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLeagues } from '@/hooks/useLeagues';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PlatformBadge } from '@/components/ui/PlatformBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { Link } from 'react-router-dom';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { PlusIcon, TrophyIcon, UsersIcon, CalendarDaysIcon } from '@heroicons/react/24/outline';
import { formatDate } from '@/utils';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { data: leagues, isLoading, error } = useLeagues();

  return (
    <PageContainer width="wide">
      <PageHeader
        title={`Welcome back, ${user?.full_name || user?.email}`}
        subtitle="Manage your fantasy football leagues and get intelligent insights."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-xl font-bold text-fg">Your Leagues</h2>
            <Link to="/leagues/connect">
              <Button size="sm">
                <PlusIcon className="h-4 w-4" />
                Connect League
              </Button>
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : error ? (
            <Card>
              <EmptyState
                icon={TrophyIcon}
                variant="error"
                title="Couldn't load your leagues"
                description={error.detail}
              />
            </Card>
          ) : !leagues || leagues.length === 0 ? (
            <Card>
              <EmptyState
                icon={TrophyIcon}
                title="No leagues connected"
                description="Connect your ESPN or Sleeper league to unlock analysis, suggestions, and weekly recaps."
                action={
                  <Link to="/leagues/connect">
                    <Button>Connect Your First League</Button>
                  </Link>
                }
              />
            </Card>
          ) : (
            <div className="space-y-4">
              {leagues.map((league) => (
                <Card key={league.id} className="transition-shadow hover:shadow-elevation-3">
                  <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h3 className="font-display text-base font-bold text-fg sm:text-lg">
                          {league.name}
                        </h3>
                        <PlatformBadge platform={league.platform || 'ESPN'} size="sm" />
                      </div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg-muted">
                        <span className="flex items-center gap-1">
                          <UsersIcon className="h-4 w-4" />
                          {league.size} teams
                        </span>
                        <span className="flex items-center gap-1">
                          <CalendarDaysIcon className="h-4 w-4" />
                          Week {league.current_week}
                        </span>
                        <span className="capitalize">{league.scoring_type} scoring</span>
                      </div>
                      <p className="mt-2 text-xs text-fg-subtle">
                        Last synced: {league.last_synced ? formatDate(league.last_synced) : 'Never'}
                      </p>
                    </div>
                    <Link to={`/leagues/${league.id}`} className="sm:flex-shrink-0">
                      <Button size="sm" variant="secondary" fullWidth className="sm:w-auto">
                        View League
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Link to="/leagues/connect" className="block">
                  <Button fullWidth variant="secondary" size="sm">
                    <PlusIcon className="h-4 w-4" />
                    Connect League
                  </Button>
                </Link>
                <Link to="/profile" className="block">
                  <Button fullWidth variant="ghost" size="sm">
                    Update ESPN Credentials
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>

          {user && !user.has_espn_credentials && (
            <Card className="border-warning-300 bg-warning-50 dark:bg-warning-900/20">
              <CardHeader className="border-warning-300/60">
                <CardTitle className="text-warning-800 dark:text-warning-300">Setup Required</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-warning-700 dark:text-warning-300/90">
                  Add your ESPN credentials to access private leagues and get real-time data.
                </p>
                <Link to="/profile">
                  <Button size="sm" fullWidth>
                    Add Credentials
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </PageContainer>
  );
};
