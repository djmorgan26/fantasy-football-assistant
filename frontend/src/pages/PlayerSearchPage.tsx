import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useSearchPlayers } from '@/hooks/usePlayers';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { getPositionColor } from '@/utils';
import {
  MagnifyingGlassIcon,
  UserIcon,
  TrophyIcon,
  FireIcon,
} from '@heroicons/react/24/outline';

export const PlayerSearchPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const { data: league } = useLeague(parseInt(leagueId || '0', 10));
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPosition, setSelectedPosition] = useState('');
  const [availableOnly, setAvailableOnly] = useState(true);
  const [shouldSearch, setShouldSearch] = useState(false);

  // Create search request object
  const searchRequest = {
    league_id: parseInt(leagueId || '0', 10),
    week: league?.current_week,
    position: selectedPosition || undefined,
    search_term: searchTerm || undefined,
    available_only: availableOnly,
  };

  // Use the search hook with the current search parameters
  const { data: searchResults, isLoading, error } = useSearchPlayers(
    searchRequest,
    shouldSearch && !!league
  );

  const players = searchResults?.players || [];
  const totalCount = searchResults?.total_count || 0;

  const handleSearch = () => {
    setShouldSearch(true);
  };

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${leagueId}`}
        backLabel="Back to League"
        title="Player Search"
        subtitle={`Search and analyze players in ${league?.name ?? 'your league'}`}
        media={<MagnifyingGlassIcon className="h-8 w-8 text-brand" />}
        mediaDesktopOnly
      />

      {/* Search Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
            <div>
              <label className="block text-sm font-medium text-fg mb-2">
                Search Players
              </label>
              <div className="relative">
                <MagnifyingGlassIcon className="h-5 w-5 text-fg-subtle absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Player name or team..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="min-h-[2.75rem] w-full rounded-lg border border-border bg-surface-raised py-2.5 pl-10 pr-4 text-fg placeholder:text-fg-subtle focus:border-brand focus-visible:ring-2 focus-visible:ring-ring sm:min-h-[2.5rem] sm:py-2 sm:text-sm"
                />
              </div>
            </div>

            <Select
              label="Position"
              value={selectedPosition}
              onChange={setSelectedPosition}
              fullWidth
              options={[
                { value: '', label: 'All Positions' },
                { value: 'QB', label: 'Quarterback' },
                { value: 'RB', label: 'Running Back' },
                { value: 'WR', label: 'Wide Receiver' },
                { value: 'TE', label: 'Tight End' },
                { value: 'K', label: 'Kicker' },
                { value: 'D/ST', label: 'Defense' },
              ]}
            />

            <div className="flex items-end">
              <label className="flex min-h-[2.75rem] cursor-pointer items-center sm:min-h-0">
                <input
                  type="checkbox"
                  checked={availableOnly}
                  onChange={(e) => setAvailableOnly(e.target.checked)}
                  className="mr-2 h-4 w-4 accent-[rgb(var(--brand))]"
                />
                <span className="text-sm text-fg">Available players only</span>
              </label>
            </div>

            <div className="flex items-end">
              <Button 
                onClick={handleSearch}
                disabled={isLoading}
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Searching...
                  </>
                ) : (
                  'Search Players'
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Search Results (<span className="tabular">{totalCount}</span> players)
            </span>
            <span className="text-sm font-normal text-fg-muted">
              Week {league?.current_week} • {league?.season_year ?? ''} Season
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <EmptyState
              icon={UserIcon}
              variant="error"
              title="Search Error"
              description="Failed to search players. Please try again."
            />
          ) : players.length === 0 ? (
            <EmptyState
              icon={UserIcon}
              title="No Players Found"
              description="Try adjusting your search criteria to find more players."
            />
          ) : (
            <div className="space-y-4" aria-live="polite">
              {players.map((player) => (
                <div
                  key={player.id}
                  className="p-4 border border-border rounded-lg hover:shadow-elevation-3 transition-shadow"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                      {/* Player Avatar */}
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand to-primary-700 font-bold text-brand-fg sm:h-12 sm:w-12">
                        {player.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>

                      {/* Player Info */}
                      <div className="min-w-0">
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-fg">{player.full_name}</h3>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPositionColor(player.position_name || '')}`}>
                            {player.position_name}
                          </span>
                          <span className="text-sm text-fg-muted">{player.pro_team_abbr}</span>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-fg-muted">
                          <span className="flex items-center">
                            <TrophyIcon className="h-4 w-4 mr-1" />
                            <span className="tabular">{player.season_points?.toFixed(1) || '0.0'}</span> pts
                          </span>
                          <span className="flex items-center">
                            <FireIcon className="h-4 w-4 mr-1" />
                            <span className="tabular">{player.projected_points?.toFixed(1) || '0.0'}</span> proj
                          </span>
                          <span><span className="tabular">{player.ownership_percentage?.toFixed(0) || '0'}</span>% owned</span>
                        </div>
                      </div>
                    </div>

                    {/* Status & Actions */}
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4">
                      <Badge variant="success" size="sm">Available</Badge>

                      <Button size="sm" variant="secondary" className="flex-1 sm:flex-none">
                        Add to Watchlist
                      </Button>

                      <Button size="sm" variant="ghost" className="flex-1 sm:flex-none">
                        View Details
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
};