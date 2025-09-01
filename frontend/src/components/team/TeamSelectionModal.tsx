import React from 'react';
import { Team } from '@/types';
import { useClaimTeam } from '@/hooks/useTeams';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { UsersIcon, XMarkIcon } from '@heroicons/react/24/outline';

interface TeamSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  teams: Team[];
  leagueId: number;
}

export const TeamSelectionModal: React.FC<TeamSelectionModalProps> = ({
  isOpen,
  onClose,
  teams,
  leagueId,
}) => {
  const claimTeam = useClaimTeam();

  const handleTeamSelect = async (team: Team) => {
    try {
      await claimTeam.mutateAsync(team.id);
      onClose();
    } catch (error) {
      // Error is handled by the mutation hook
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <Card className="max-w-4xl w-full max-h-[80vh] overflow-y-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center">
              <UsersIcon className="h-5 w-5 mr-2" />
              Select Your Team
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="p-1"
            >
              <XMarkIcon className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-gray-600 text-sm mt-2">
            Please select which team belongs to you in this league. This will help us show you personalized information like your matchups and strategic suggestions.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {teams.map((team) => (
              <button
                key={team.id}
                onClick={() => handleTeamSelect(team)}
                disabled={claimTeam.isLoading}
                className="p-4 border rounded-lg hover:bg-gray-50 hover:shadow-md transition-all cursor-pointer border-l-4 border-l-blue-500 text-left disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <div className="flex items-center space-x-4">
                  {/* Team Logo */}
                  <div className="flex-shrink-0">
                    <img
                      src={team.logo_url}
                      alt={`${team.name} logo`}
                      className="w-12 h-12 rounded-full object-cover bg-gray-100"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                      {team.abbreviation || team.name?.charAt(0) || '?'}
                    </div>
                  </div>
                  
                  {/* Team Info */}
                  <div className="flex-1 min-w-0">
                    <div>
                      <h4 className="font-semibold text-gray-900 text-lg mb-1">
                        {team.name}
                      </h4>
                      <p className="text-sm text-gray-500 mb-2">
                        {team.abbreviation}
                      </p>
                      <div className="flex items-center space-x-3 text-sm">
                        <span className="font-medium text-gray-900">
                          {team.wins}-{team.losses}
                          {team.ties > 0 && `-${team.ties}`}
                        </span>
                        <span className="text-green-600 font-medium">
                          {team.points_for.toFixed(1)} PF
                        </span>
                        <span className="text-red-500">
                          {team.points_against.toFixed(1)} PA
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {claimTeam.isLoading && (
                  <div className="flex justify-center mt-2">
                    <LoadingSpinner size="sm" />
                  </div>
                )}
              </button>
            ))}
          </div>
          
          <div className="mt-6 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-500 text-center">
              You can change your team selection later by re-syncing the league data.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};