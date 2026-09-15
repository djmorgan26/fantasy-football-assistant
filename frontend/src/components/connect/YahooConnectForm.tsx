import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

import api, { getAuthToken } from '@/services/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

type YahooLeague = { league_key: string; name: string; season: number; num_teams: number };

export const YahooConnectForm: React.FC = () => {
  const navigate = useNavigate();
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [connected, setConnected] = useState(false);
  const [leagues, setLeagues] = useState<YahooLeague[]>([]);
  const [busy, setBusy] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);

  // This form mounts after the platform chooser changes views. Supply the
  // persisted token at request time rather than relying solely on Axios's
  // in-memory default header, which can be missing after that transition.
  const sessionConfig = useCallback(() => {
    const token = getAuthToken();
    return token ? { headers: { 'X-Fantasy-Session': token } } : undefined;
  }, []);

  const getYahoo = useCallback(<T,>(path: string) => {
    const config = sessionConfig();
    return config ? api.get<T>(path, config) : api.get<T>(path);
  }, [sessionConfig]);

  const load = useCallback(async () => {
    try {
      const status = await getYahoo<{ configured: boolean; connected: boolean }>('/yahoo/status');
      setConfigured(status.data.configured);
      setConnected(status.data.connected);
      if (status.data.connected) {
        const result = await getYahoo<YahooLeague[]>('/yahoo/leagues');
        setLeagues(result.data);
      }
    } catch (error: any) {
      const detail = error.detail || error?.response?.data?.detail || 'Could not load Yahoo leagues';
      setOauthError(detail);
      toast.error(detail);
    }
  }, [getYahoo]);

  // The OAuth callback returns to this screen with ?yahoo=connected|failed|
  // cancelled and a reason. Nothing read those, so a failed Yahoo sign-in
  // looked identical to never having pressed the button.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const outcome = params.get('yahoo');
    if (!outcome) return;
    const reason = params.get('yahoo_reason');
    if (outcome === 'connected') {
      toast.success('Yahoo account connected. Choose your league below.');
    } else {
      setOauthError(reason || (outcome === 'cancelled'
        ? 'Yahoo sign-in was cancelled before it finished.'
        : 'Yahoo sign-in did not complete.'));
    }
    params.delete('yahoo');
    params.delete('yahoo_reason');
    const query = params.toString();
    window.history.replaceState({}, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const authorize = async () => {
    setBusy(true);
    setOauthError(null);
    try {
      const body = {
        // Yahoo must return to this exact frontend origin: it is where the
        // active Fantasy Hub session is stored, even on a preview deployment.
        return_to: window.location.origin,
      };
      const config = sessionConfig();
      const result = config
        ? await api.post<{ authorization_url: string }>('/yahoo/authorize', body, config)
        : await api.post<{ authorization_url: string }>('/yahoo/authorize', body);
      window.location.assign(result.data.authorization_url);
    } catch (error: any) {
      setBusy(false);
      toast.error(error.detail || 'Yahoo is not available yet');
    }
  };

  const connect = async (leagueKey: string) => {
    setBusy(true);
    try {
      const body = { league_key: leagueKey };
      const config = sessionConfig();
      const result = config
        ? await api.post('/yahoo/connect', body, config)
        : await api.post('/yahoo/connect', body);
      toast.success(result.data.message);
      navigate('/dashboard');
    } catch (error: any) {
      toast.error(error.detail || 'Could not connect that Yahoo league');
    } finally { setBusy(false); }
  };

  if (configured === null) return <div className="flex justify-center py-8"><LoadingSpinner /></div>;
  if (!configured) return (
    <Card className="border-warning-300 bg-warning-50 dark:border-warning-900/40 dark:bg-warning-900/20"><CardContent className="p-4 text-sm text-fg-muted">
      Yahoo connection is ready in the app, but this deployment still needs its Yahoo OAuth client ID, secret, and callback URL configured.
    </CardContent></Card>
  );
  return <div className="space-y-5">
    <Card className="border-[#6001d2]/30 bg-[#6001d2]/5"><CardContent className="p-4"><div className="flex gap-3 text-sm text-fg-muted">
      <InformationCircleIcon className="h-5 w-5 shrink-0 text-[#6001d2]" />
      <div><p className="font-semibold text-fg">Sign in to Yahoo to add this league to your account</p><p className="mt-1">This is not another Fantasy Hub login. Sign in with the Yahoo account that owns your Fantasy league—it can use a different email from your Fantasy Hub (Google) login. After you approve Yahoo, we securely save its leagues to this Fantasy Hub account for future visits.</p></div>
    </div></CardContent></Card>
    {oauthError && <Card className="border-error-300 bg-error-50 dark:border-error-900/40 dark:bg-error-900/20"><CardContent className="p-4 text-sm">
      <p className="font-semibold text-fg">Yahoo sign-in did not finish</p>
      <p className="mt-1 break-words text-fg-muted">{oauthError}</p>
    </CardContent></Card>}
    {!connected ? <Button className="w-full" disabled={busy} onClick={authorize}>{busy ? 'Opening Yahoo…' : 'Sign in to Yahoo'}</Button> : (
      <><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-medium text-fg">Choose a Yahoo Fantasy Football league</p><Button type="button" variant="ghost" size="sm" disabled={busy} onClick={authorize}>Use another Yahoo account</Button></div>
      {leagues.length ? <div className="space-y-2">{leagues.map((league) => <button key={league.league_key} disabled={busy} onClick={() => void connect(league.league_key)} className="w-full rounded-lg border border-border p-3 text-left hover:border-[#6001d2] hover:bg-[#6001d2]/5 disabled:opacity-50"><div className="font-semibold text-fg">{league.name}</div><div className="text-xs text-fg-subtle">{league.season} · {league.num_teams} teams</div></button>)}</div> : <Card className="border-warning-300 bg-warning-50 dark:border-warning-900/40 dark:bg-warning-900/20"><CardContent className="p-4 text-sm text-fg-muted"><p className="font-semibold text-fg">Yahoo is connected, but this Yahoo account has no Fantasy Football leagues.</p><p className="mt-1">This usually means a different Yahoo account owns the league. Select <span className="font-medium text-fg">Use another Yahoo account</span> above, then sign in to the Yahoo account you use at fantasy.yahoo.com.</p></CardContent></Card>}</>
    )}
    <Button type="button" variant="ghost" onClick={() => navigate('/dashboard')} disabled={busy}>Cancel</Button>
  </div>;
};
