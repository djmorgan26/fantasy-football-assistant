import React from 'react';
import { Team } from '@/types';
import { useClaimTeam } from '@/hooks/useTeams';
import { Modal } from '@/components/ui/Modal';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="xl"
      title="Select Your Team"
      description="Pick the team that belongs to you in this league. We use it to personalize your matchups and strategic suggestions."
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {teams.map((team) => (
          <button
            key={team.id}
            onClick={() => handleTeamSelect(team)}
            disabled={claimTeam.isLoading}
            className="cursor-pointer rounded-lg border border-border border-l-4 border-l-brand bg-surface-raised p-4 text-left transition-all hover:bg-surface-sunken hover:shadow-elevation-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <div className="flex items-center space-x-4">
              <div className="relative flex-shrink-0">
                <img
                  src={team.logo_url}
                  alt={`${team.name} logo`}
                  className="h-12 w-12 rounded-full bg-surface-sunken object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-brand to-primary-800 text-sm font-bold text-brand-fg">
                  {team.abbreviation || team.name?.charAt(0) || '?'}
                </div>
              </div>

              <div className="min-w-0 flex-1">
                <h4 className="mb-1 font-display text-lg font-bold text-fg">{team.name}</h4>
                <p className="mb-2 text-sm text-fg-subtle">{team.abbreviation}</p>
                <div className="flex items-center space-x-3 text-sm">
                  <span className="font-medium text-fg tabular">
                    {team.wins}-{team.losses}
                    {team.ties > 0 && `-${team.ties}`}
                  </span>
                  <span className="font-medium text-success-600 tabular">
                    {team.points_for.toFixed(1)} PF
                  </span>
                  <span className="text-error-500 tabular">
                    {team.points_against.toFixed(1)} PA
                  </span>
                </div>
              </div>
            </div>

            {claimTeam.isLoading && (
              <div className="mt-2 flex justify-center">
                <LoadingSpinner size="sm" />
              </div>
            )}
          </button>
        ))}
      </div>

      <p className="mt-6 border-t border-border pt-4 text-center text-sm text-fg-subtle">
        You can change your team selection later by re-syncing the league data.
      </p>
    </Modal>
  );
};
