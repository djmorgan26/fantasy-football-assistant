import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLeagues } from '@/hooks/useLeagues';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Link } from 'react-router-dom';
import { PlusIcon, TrophyIcon, UsersIcon } from '@heroicons/react/24/outline';
import { formatDate, formatRecord } from '@/utils';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { data: leagues, isLoading, error } = useLeagues();

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="mt-12" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent>
            <p className="text-error-600">Failed to load leagues: {error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name || user?.email}!
        </h1>
        <p className="text-gray-600 mt-2">
          Manage your fantasy football leagues and get intelligent insights.
        </p>
      </div>

      {/* League Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Your Leagues</h2>
            <Link to="/leagues/connect">
              <Button size="sm" className="flex items-center space-x-1">
                <PlusIcon className="h-4 w-4" />
                <span>Connect League</span>
              </Button>
            </Link>
          </div>

          {!leagues || leagues.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <TrophyIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No leagues connected
                </h3>
                <p className="text-gray-600 mb-4">
                  Connect your ESPN fantasy league to get started with intelligent analysis and recommendations.
                </p>
                <Link to="/leagues/connect">
                  <Button>Connect Your First League</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {leagues.map((league) => (
                <Card key={league.id} className="hover:shadow-lg transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-lg text-gray-900 mb-1">
                          {league.name}
                        </h3>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span className="flex items-center">
                            <UsersIcon className="h-4 w-4 mr-1" />
                            {league.size} teams
                          </span>
                          <span>Week {league.current_week}</span>
                          <span className="capitalize">{league.scoring_type} scoring</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          Last synced: {league.last_synced ? formatDate(league.last_synced) : 'Never'}
                        </p>
                      </div>
                      <div className="flex space-x-2">
                        <Link to={`/leagues/${league.id}`}>
                          <Button size="sm" variant="secondary">
                            View League
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Link to="/leagues/connect" className="block">
                  <Button fullWidth variant="secondary" size="sm">
                    <PlusIcon className="h-4 w-4 mr-2" />
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
            <Card className="border-warning-200 bg-warning-50">
              <CardHeader>
                <CardTitle className="text-warning-800">Setup Required</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-warning-700 text-sm mb-3">
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
    </div>
  );
};