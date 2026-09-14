import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useConnectLeague } from '@/hooks/useLeagues';
import { LeagueConnectionRequest } from '@/types';

const schema = z.object({
  league_id: z
    .string()
    .min(1, 'League ID is required')
    .transform((val) => parseInt(val, 10))
    .refine((val) => !isNaN(val) && val > 0, 'League ID must be a valid number'),
  espn_s2: z.string().optional(),
  espn_swid: z.string().optional(),
});

type EspnForm = z.infer<typeof schema>;

/**
 * Pull the league id out of whatever the user pasted.
 *
 * ESPN writes the id two different ways depending on where you copied the
 * link from, and someone who pastes a URL that happens to use the other shape
 * should not be told their league ID is invalid.
 */
export const extractLeagueId = (text: string): string => {
  const trimmed = (text || '').trim();
  const query = trimmed.match(/[?&]leagueId=(\d+)/i);      // ...?leagueId=123
  if (query) return query[1];
  const path = trimmed.match(/\/leagues?\/(\d+)/i);        // .../league/123
  if (path) return path[1];
  if (/^\d+$/.test(trimmed)) return trimmed;               // already just an id
  return '';
};

export const EspnConnectForm: React.FC = () => {
  const navigate = useNavigate();
  const connectLeague = useConnectLeague();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
  } = useForm<EspnForm>({ resolver: zodResolver(schema) });

  const watchedLeagueId = watch('league_id');
  const watchedEspnS2 = watch('espn_s2');
  const watchedEspnSwid = watch('espn_swid');

  const onSubmit = async (data: EspnForm) => {
    try {
      const payload: LeagueConnectionRequest = { league_id: data.league_id };
      if (data.espn_s2?.trim()) payload.espn_s2 = data.espn_s2.trim();
      if (data.espn_swid?.trim()) payload.espn_swid = data.espn_swid.trim();

      const result = await connectLeague.mutateAsync(payload);
      if (result.success) {
        toast.success('League connected');
        // Give the query cache a beat to invalidate before the dashboard reads it.
        setTimeout(() => navigate('/dashboard'), 500);
      }
    } catch (error) {
      console.error('Failed to connect league:', error);
    }
  };

  /** Rewrite a pasted URL to the bare id, so the field never holds a URL. */
  const handlePaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    const extracted = extractLeagueId(event.clipboardData.getData('text'));
    if (extracted) {
      event.preventDefault();
      setValue('league_id', extracted as unknown as number, { shouldValidate: true });
      toast.success('Found the league ID in that link');
    }
  };

  const busy = isSubmitting || connectLeague.isLoading;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <Card className="border-brand/30 bg-brand/5">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <InformationCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-brand" />
            <div className="text-sm text-fg-muted">
              <p className="font-semibold text-fg">Where to find it</p>
              <p className="mt-1">
                Open your league on ESPN and paste the whole address bar below. We pull
                the ID out of it. A public league needs nothing else.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div>
        <label htmlFor="league_id" className="mb-2 block text-sm font-medium text-fg">
          League ID or league URL <span className="text-error-500">*</span>
        </label>
        <Input
          id="league_id"
          type="text"
          inputMode="numeric"
          fullWidth
          placeholder="1725275280, or paste the full ESPN link"
          {...register('league_id')}
          onPaste={handlePaste}
          error={errors.league_id?.message}
          disabled={busy}
          className="font-mono"
        />
        {watchedLeagueId ? (
          <p className="mt-2 flex items-center text-sm text-success-600">
            <CheckCircleIcon className="mr-1 h-4 w-4" />
            League ID: {watchedLeagueId}
          </p>
        ) : null}
      </div>

      <div className="border-t border-border pt-4">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center text-sm text-fg-muted hover:text-fg"
        >
          <ExclamationTriangleIcon className="mr-1 h-4 w-4" />
          {showAdvanced ? 'Hide' : 'My league is private'}
        </button>
      </div>

      {showAdvanced && (
        <div className="space-y-4 rounded-lg border border-border bg-surface-sunken p-4">
          <p className="text-sm text-fg-muted">
            A private league needs two cookies from your logged-in ESPN session. They are
            encrypted before they are stored and only used to read your league.
          </p>

          <div>
            <label htmlFor="espn_s2" className="mb-2 block text-sm font-medium text-fg">
              ESPN S2 cookie
            </label>
            <Input
              id="espn_s2"
              type="password"
              fullWidth
              placeholder="espn_s2 value"
              {...register('espn_s2')}
              error={errors.espn_s2?.message}
              disabled={busy}
            />
          </div>

          <div>
            <label htmlFor="espn_swid" className="mb-2 block text-sm font-medium text-fg">
              ESPN SWID cookie
            </label>
            <Input
              id="espn_swid"
              type="text"
              fullWidth
              placeholder="usually starts with {"
              {...register('espn_swid')}
              error={errors.espn_swid?.message}
              disabled={busy}
            />
          </div>

          {(watchedEspnS2 || watchedEspnSwid) && (
            <div className="rounded-md border border-warning-200 bg-warning-50 p-3 dark:border-warning-900/40 dark:bg-warning-900/20">
              <div className="flex items-start">
                <ExclamationTriangleIcon className="mr-2 mt-0.5 h-5 w-5 text-warning-500" />
                <p className="text-sm text-warning-800 dark:text-warning-300">
                  These are encrypted at rest and never leave this app.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Button type="submit" disabled={busy} className="flex-1">
          {busy ? (
            <>
              <LoadingSpinner size="sm" className="mr-2" />
              Connecting...
            </>
          ) : (
            'Connect league'
          )}
        </Button>
        <Button type="button" variant="ghost" onClick={() => navigate('/dashboard')} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  );
};
