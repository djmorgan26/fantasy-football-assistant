import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { PlatformBadge } from '@/components/ui/PlatformBadge';
import { SleeperLeagueConnectionRequest } from '@/types';
import api from '@/services/api';
import { sleeperService, SleeperLeagueSummary } from '@/services/sleeper';
import { cn } from '@/utils';
import {
  LinkIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { PageContainer, PageHeader } from '@/components/layout/Page';

const sleeperConnectionSchema = z.object({
  league_id: z.string().min(1, 'Pick which league to connect'),
  sleeper_user_id: z.string().min(1, 'Your Sleeper username is required'),
});

type SleeperConnectionForm = z.infer<typeof sleeperConnectionSchema>;

export const SleeperConnectPage: React.FC = () => {
  const navigate = useNavigate();
  const [isConnecting, setIsConnecting] = useState(false);
  const [isFinding, setIsFinding] = useState(false);
  const [found, setFound] = useState<SleeperLeagueSummary[]>([]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    getValues,
    formState: { errors },
  } = useForm<SleeperConnectionForm>({
    resolver: zodResolver(sleeperConnectionSchema),
  });

  /**
   * Look up which leagues a username is in.
   *
   * Tries the current NFL season first and falls back a year, because someone
   * connecting in the offseason has last season's leagues and no new ones yet.
   */
  const findLeagues = async () => {
    const username = (getValues('sleeper_user_id') || '').trim();
    if (!username) {
      toast.error('Enter your Sleeper username first');
      return;
    }

    setIsFinding(true);
    setFound([]);
    try {
      const thisYear = new Date().getFullYear();
      for (const season of [thisYear, thisYear - 1]) {
        const result = await sleeperService.findLeagues(username, season);
        if (result.leagues.length > 0) {
          setFound(result.leagues);
          if (result.leagues.length === 1) {
            setValue('league_id', result.leagues[0].league_id);
          }
          toast.success(
            `Found ${result.leagues.length} league${result.leagues.length === 1 ? '' : 's'}`
          );
          return;
        }
      }
      toast.error(`No leagues found for "${username}"`);
    } catch (error: any) {
      toast.error(error?.detail || `Could not find a Sleeper user called "${username}"`);
    } finally {
      setIsFinding(false);
    }
  };

  const onSubmit = async (data: SleeperConnectionForm) => {
    setIsConnecting(true);
    try {
      const connectionData: SleeperLeagueConnectionRequest = {
        league_id: data.league_id.trim(),
        sleeper_user_id: data.sleeper_user_id.trim(),
      };

      const response = await api.post('/sleeper/connect', connectionData);

      if (response.data.success) {
        toast.success(`Connected to ${response.data.league_name}!`);
        setTimeout(() => {
          navigate('/dashboard');
        }, 500);
      }
    } catch (error: any) {
      console.error('Failed to connect Sleeper league:', error);
      toast.error(error.detail || 'Failed to connect league. Please check your information.');
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <PageContainer width="narrow">
      <PlatformBadge platform="sleeper" size="md" className="mb-3" />
      <PageHeader
        title="Connect Your Sleeper League"
        subtitle="Link your Sleeper fantasy football league to unlock AI-powered insights"
      />

      {/* Info Banner */}
      <Card className="mb-6 bg-brand/5 border-brand/30">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <InformationCircleIcon className="h-6 w-6 text-brand flex-shrink-0 mt-0.5" />
            <div className="text-sm text-fg-muted">
              <p className="font-semibold mb-2">All you need is your username</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Open Sleeper and tap your avatar — your username is at the top</li>
                <li>Type it below and hit <strong>Find my leagues</strong></li>
                <li>Pick the league you want and connect it</li>
              </ol>
              <p className="mt-2">
                Sleeper's data is public and read-only, so this needs no password and no
                league ID.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connection Form */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <LinkIcon className="h-6 w-6 text-brand" />
            <CardTitle>League Connection</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Find the leagues for a username. Sleeper's API is public and
                read-only, so a username is all this needs — no password, no
                token, and no league id dug out of a URL. */}
            <div>
              <label htmlFor="sleeper_user_id" className="block text-sm font-medium text-fg mb-2">
                Your Sleeper username <span className="text-error-500">*</span>
              </label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="sleeper_user_id"
                  fullWidth
                  {...register('sleeper_user_id')}
                  placeholder="the name you log in with"
                  error={errors.sleeper_user_id?.message}
                  disabled={isConnecting}
                />
                <Button
                  type="button"
                  variant="secondary"
                  loading={isFinding}
                  disabled={isConnecting}
                  onClick={findLeagues}
                  className="sm:w-auto"
                >
                  <MagnifyingGlassIcon className="h-4 w-4" />
                  Find my leagues
                </Button>
              </div>
              <p className="mt-1 text-xs text-fg-muted">
                No password needed — Sleeper's data is public.
              </p>
            </div>

            {found.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium text-fg">
                  {found.length === 1
                    ? 'Found 1 league'
                    : `Found ${found.length} leagues — pick one`}
                </p>
                <div className="flex flex-col gap-2">
                  {found.map((league) => (
                    <button
                      key={league.league_id}
                      type="button"
                      onClick={() => setValue('league_id', league.league_id)}
                      className={cn(
                        'rounded-lg border p-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        watch('league_id') === league.league_id
                          ? 'border-brand bg-brand/5'
                          : 'border-border hover:border-border-strong hover:bg-surface-sunken'
                      )}
                    >
                      <div className="font-semibold text-fg">{league.name}</div>
                      <div className="text-xs text-fg-subtle">
                        {league.season} · {league.total_rosters} teams
                        {league.status ? ` · ${league.status.replace(/_/g, ' ')}` : ''}
                      </div>
                    </button>
                  ))}
                </div>
                {errors.league_id && (
                  <p className="mt-1 text-sm text-error-600">{errors.league_id.message}</p>
                )}
              </div>
            )}

            {/* Benefits List */}
            <div className="bg-surface-sunken rounded-lg p-4">
              <p className="text-sm font-semibold text-fg mb-3">
                What you'll get:
              </p>
              <ul className="space-y-2">
                {[
                  'AI-powered trade analysis and recommendations',
                  'Strategic suggestions to improve your team',
                  'Live roster and matchup tracking',
                  'Performance insights and trends',
                ].map((benefit, index) => (
                  <li key={index} className="flex items-start text-sm text-fg-muted">
                    <CheckCircleIcon className="h-5 w-5 text-success-500 mr-2 flex-shrink-0" />
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Submit Button */}
            <div className="flex space-x-3">
              <Button
                type="submit"
                variant="primary"
                disabled={isConnecting}
                className="flex-1"
              >
                {isConnecting ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <LinkIcon className="h-5 w-5 mr-2" />
                    Connect League
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate('/dashboard')}
                disabled={isConnecting}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Help Text */}
      <div className="mt-6 text-center">
        <p className="text-sm text-fg-muted">
          No API key required - Sleeper data is public and free! 🎉
        </p>
      </div>
    </PageContainer>
  );
};
