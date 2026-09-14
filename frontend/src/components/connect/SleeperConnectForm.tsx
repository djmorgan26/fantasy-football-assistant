import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  InformationCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import api from '@/services/api';
import { sleeperService, SleeperLeagueSummary } from '@/services/sleeper';
import { SleeperLeagueConnectionRequest } from '@/types';
import { cn } from '@/utils';

const schema = z.object({
  league_id: z.string().min(1, 'Pick which league to connect'),
  sleeper_user_id: z.string().min(1, 'Your Sleeper username is required'),
});

type SleeperForm = z.infer<typeof schema>;

export const SleeperConnectForm: React.FC = () => {
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
  } = useForm<SleeperForm>({ resolver: zodResolver(schema) });

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
            setValue('league_id', result.leagues[0].league_id, { shouldValidate: true });
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

  const onSubmit = async (data: SleeperForm) => {
    setIsConnecting(true);
    try {
      const payload: SleeperLeagueConnectionRequest = {
        league_id: data.league_id.trim(),
        sleeper_user_id: data.sleeper_user_id.trim(),
      };
      const response = await api.post('/sleeper/connect', payload);
      if (response.data.success) {
        toast.success(`Connected to ${response.data.league_name}`);
        setTimeout(() => navigate('/dashboard'), 500);
      }
    } catch (error: any) {
      console.error('Failed to connect Sleeper league:', error);
      toast.error(error.detail || 'Could not connect that league. Check the details and retry.');
    } finally {
      setIsConnecting(false);
    }
  };

  const selected = watch('league_id');

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <Card className="border-brand/30 bg-brand/5">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <InformationCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-brand" />
            <div className="text-sm text-fg-muted">
              <p className="font-semibold text-fg">All you need is your username</p>
              <p className="mt-1">
                Open Sleeper and tap your avatar; your username is at the top. Sleeper's
                data is public and read-only, so there is no password and no league ID to
                dig out of a URL.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sleeper's API is public, so a username is enough to list someone's
          leagues. Finding them beats asking for an id the user would have to
          go copy. */}
      <div>
        <label htmlFor="sleeper_user_id" className="mb-2 block text-sm font-medium text-fg">
          Your Sleeper username <span className="text-error-500">*</span>
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="sleeper_user_id"
            fullWidth
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
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
      </div>

      {found.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-fg">
            {found.length === 1 ? 'Found 1 league' : `Found ${found.length} leagues, pick one`}
          </p>
          <div className="flex flex-col gap-2">
            {found.map((league) => (
              <button
                key={league.league_id}
                type="button"
                aria-pressed={selected === league.league_id}
                onClick={() =>
                  setValue('league_id', league.league_id, { shouldValidate: true })
                }
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  selected === league.league_id
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

      <div className="flex gap-3">
        <Button type="submit" disabled={isConnecting} className="flex-1">
          {isConnecting ? (
            <>
              <LoadingSpinner size="sm" className="mr-2" />
              Connecting...
            </>
          ) : (
            'Connect league'
          )}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => navigate('/dashboard')}
          disabled={isConnecting}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
};
