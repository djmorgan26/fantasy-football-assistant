import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useSearchPlayers } from '@/hooks/usePlayers';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Player } from '@/types';
import {
  ArrowLeftIcon,
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

  const getStatusBadge = (status: string, owner?: string) => {
    switch (status) {
      case 'available':
        return <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Available</span>;
      case 'waivers':
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">Waivers</span>;
      case 'owned':
        return <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">Owned by {owner}</span>;
      default:
        return null;
    }
  };

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'QB': return 'text-purple-600 bg-purple-100';
      case 'RB': return 'text-green-600 bg-green-100';
      case 'WR': return 'text-blue-600 bg-blue-100';
      case 'TE': return 'text-orange-600 bg-orange-100';
      case 'K': return 'text-pink-600 bg-pink-100';
      case 'D/ST': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Link
            to={`/leagues/${leagueId}`}
            className="flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to League
          </Link>
        </div>
        
        <div className="flex items-center">
          <MagnifyingGlassIcon className="h-8 w-8 text-blue-600 mr-3" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Player Search
            </h1>
            <p className="text-gray-600">
              Search and analyze players in {league?.name}
            </p>
          </div>
        </div>
      </div>

      {/* Search Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Players
              </label>
              <div className="relative">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Player name or team..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Position
              </label>
              <select
                value={selectedPosition}
                onChange={(e) => setSelectedPosition(e.target.value)}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="ALL">All Positions</option>
                <option value="QB">Quarterback</option>
                <option value="RB">Running Back</option>
                <option value="WR">Wide Receiver</option>
                <option value="TE">Tight End</option>
                <option value="K">Kicker</option>
                <option value="D/ST">Defense</option>
              </select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={availableOnly}
                  onChange={(e) => setAvailableOnly(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Available players only</span>
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
          <CardTitle className="flex items-center justify-between">
            <span>Search Results ({totalCount} players)</span>
            <div className="text-sm text-gray-500">
              Week {league?.current_week} • 2024 Season
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <UserIcon className="h-12 w-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Search Error
              </h3>
              <p className="text-gray-600">
                Failed to search players. Please try again.
              </p>
            </div>
          ) : players.length === 0 ? (
            <div className="text-center py-12">
              <UserIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Players Found
              </h3>
              <p className="text-gray-600">
                Try adjusting your search criteria to find more players.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {players.map((player) => (
                <div
                  key={player.id}
                  className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      {/* Player Avatar */}
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                        {player.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>
                      
                      {/* Player Info */}
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="font-semibold text-gray-900">{player.full_name}</h3>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPositionColor(player.position_name || '')}`}>
                            {player.position_name}
                          </span>
                          <span className="text-sm text-gray-600">{player.pro_team_abbr}</span>
                        </div>
                        
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span className="flex items-center">
                            <TrophyIcon className="h-4 w-4 mr-1" />
                            {player.season_points?.toFixed(1) || '0.0'} pts
                          </span>
                          <span className="flex items-center">
                            <FireIcon className="h-4 w-4 mr-1" />
                            {player.projected_points?.toFixed(1) || '0.0'} proj
                          </span>
                          <span>{player.ownership_percentage?.toFixed(0) || '0'}% owned</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Status & Actions */}
                    <div className="flex items-center space-x-4">
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Available</span>
                      
                      <Button size="sm" variant="secondary">
                        Add to Watchlist
                      </Button>
                      
                      <Button size="sm" variant="ghost">
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
    </div>
  );
};