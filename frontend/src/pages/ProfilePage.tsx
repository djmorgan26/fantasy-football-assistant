import React from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { extractESPNCookies } from '@/utils';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { PlatformBadge } from '@/components/ui/PlatformBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useLeagues } from '@/hooks/useLeagues';
import { TrophyIcon, PlusIcon } from '@heroicons/react/24/outline';

// The "you must supply your current password" rule cannot hold for an account
// that has never had one, so the schema depends on the account it validates.
const buildProfileSchema = (hasPassword: boolean) =>
  z
    .object({
      full_name: z.string().optional(),
      current_password: z.string().optional(),
      new_password: z
        .string()
        .min(8, 'Password must be at least 8 characters')
        .optional()
        .or(z.literal('')),
      espn_cookies: z.string().optional(),
      espn_s2: z.string().optional(),
      espn_swid: z.string().optional(),
    })
    .refine((data) => !hasPassword || !data.new_password || !!data.current_password, {
      message: 'Current password is required to set a new password',
      path: ['current_password'],
    });

type ProfileFormData = z.infer<ReturnType<typeof buildProfileSchema>>;

export const ProfilePage: React.FC = () => {
  const { user, updateProfile } = useAuth();
  const { data: leagues, isLoading: leaguesLoading } = useLeagues();

  // Credentials are an ESPN-only concern: Sleeper's data is public and
  // read-only. Showing one "credentials" status for the whole account read as
  // though a connected Sleeper league were somehow unauthenticated.
  const espnLeagues = (leagues || []).filter((l) => l.platform === 'espn');
  const sleeperLeagues = (leagues || []).filter((l) => l.platform === 'sleeper');

  // Defaults to true so the form does not flash the "set your first password"
  // wording while /auth/me is still in flight.
  const hasPassword = user?.has_password ?? true;

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(buildProfileSchema(hasPassword)),
    defaultValues: {
      full_name: user?.full_name || '',
    },
  });

  const espnCookiesField = register('espn_cookies');

  const handlePasteCookies = (event: React.ChangeEvent<HTMLInputElement>) => {
    espnCookiesField.onChange(event);
    const { espn_s2, swid } = extractESPNCookies(event.target.value);
    if (espn_s2) {
      setValue('espn_s2', espn_s2, { shouldDirty: true });
    }
    if (swid) {
      setValue('espn_swid', swid, { shouldDirty: true });
    }
  };

  const onSubmit = async (data: ProfileFormData) => {
    const updates: {
      full_name?: string;
      current_password?: string;
      new_password?: string;
      espn_s2?: string;
      espn_swid?: string;
    } = {};

    if (data.full_name?.trim()) {
      updates.full_name = data.full_name.trim();
    }
    if (data.new_password?.trim()) {
      updates.new_password = data.new_password.trim();
      if (data.current_password?.trim()) {
        updates.current_password = data.current_password.trim();
      }
    }
    if (data.espn_s2?.trim()) {
      updates.espn_s2 = data.espn_s2.trim();
    }
    if (data.espn_swid?.trim()) {
      updates.espn_swid = data.espn_swid.trim();
    }

    try {
      await updateProfile(updates);
      reset({
        full_name: updates.full_name ?? data.full_name ?? '',
        current_password: '',
        new_password: '',
        espn_cookies: '',
        espn_s2: '',
        espn_swid: '',
      });
    } catch (error) {
      // Error handling is done in the AuthContext
    }
  };

  return (
    <PageContainer width="narrow">
      <PageHeader
        title="Profile"
        subtitle="Your account, your connected leagues, and the credentials only ESPN needs."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <dt className="text-sm text-fg-muted">Full name</dt>
                <dd className="flex items-center gap-2 text-sm font-medium text-fg">
                  {user?.avatar_url && (
                    <img
                      src={user.avatar_url}
                      alt=""
                      className="h-7 w-7 rounded-full border border-border object-cover"
                      referrerPolicy="no-referrer"
                    />
                  )}
                  {user?.full_name || 'Not set'}
                </dd>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <dt className="text-sm text-fg-muted">Email</dt>
                <dd className="break-all text-sm font-medium text-fg">{user?.email}</dd>
              </div>
              {user?.created_at && (
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                  <dt className="text-sm text-fg-muted">Member since</dt>
                  <dd className="text-sm font-medium text-fg">
                    {new Date(user.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </dd>
                </div>
              )}
              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <dt className="text-sm text-fg-muted">
                  Sign-in methods
                  <span className="block text-xs text-fg-subtle">
                    How you get into this account
                  </span>
                </dt>
                <dd className="flex flex-wrap items-center gap-1.5">
                  <Badge variant={user?.has_google ? 'success' : 'default'} size="sm">
                    {user?.has_google ? 'Google linked' : 'Google not linked'}
                  </Badge>
                  <Badge variant={hasPassword ? 'success' : 'warning'} size="sm">
                    {hasPassword ? 'Password set' : 'No password'}
                  </Badge>
                </dd>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <dt className="text-sm text-fg-muted">
                  ESPN credentials
                  <span className="block text-xs text-fg-subtle">
                    Only needed for private ESPN leagues
                  </span>
                </dt>
                <dd>
                  {user?.has_espn_credentials ? (
                    <Badge variant="success" size="sm">
                      Saved
                    </Badge>
                  ) : espnLeagues.length > 0 ? (
                    <Badge variant="warning" size="sm">
                      Not saved
                    </Badge>
                  ) : (
                    <Badge variant="default" size="sm">
                      Not needed
                    </Badge>
                  )}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Connected leagues</CardTitle>
            <p className="mt-1 text-sm text-fg-muted">
              {sleeperLeagues.length > 0 && espnLeagues.length > 0
                ? 'Both platforms are connected.'
                : 'Connect as many leagues as you like, on either platform.'}
            </p>
          </CardHeader>
          <CardContent>
            {leaguesLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-14 w-full rounded-lg" />
                <Skeleton className="h-14 w-full rounded-lg" />
              </div>
            ) : (leagues || []).length === 0 ? (
              <EmptyState
                icon={TrophyIcon}
                title="No leagues yet"
                description="Connect an ESPN or Sleeper league to get started."
                action={
                  <Link to="/leagues/connect">
                    <Button size="sm">
                      <PlusIcon className="mr-1.5 h-4 w-4" />
                      Connect a league
                    </Button>
                  </Link>
                }
              />
            ) : (
              <>
                <ul className="space-y-2">
                  {(leagues || []).map((league) => (
                    <li key={league.id}>
                      <Link
                        to={`/leagues/${league.id}`}
                        className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-lg border border-border p-3 transition-colors hover:border-border-strong hover:bg-surface-sunken focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <span className="flex min-w-0 items-center gap-2">
                          <PlatformBadge platform={league.platform} size="sm" />
                          <span className="truncate font-semibold text-fg">{league.name}</span>
                        </span>
                        <span className="shrink-0 text-xs text-fg-subtle">
                          {league.season_year} · {league.size} teams ·{' '}
                          {league.scoring_type.replace(/_/g, ' ')}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <Link to="/leagues/connect" className="mt-3 inline-block">
                  <Button variant="secondary" size="sm">
                    <PlusIcon className="mr-1.5 h-4 w-4" />
                    Connect another
                  </Button>
                </Link>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Update Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div className="space-y-4">
                <Input
                  label="Full Name"
                  type="text"
                  {...register('full_name')}
                  error={errors.full_name?.message}
                  fullWidth
                  placeholder="Enter your full name"
                  autoComplete="name"
                />
              </div>

              <div className="border-t border-border pt-6">
                <h4 className="mb-1 text-sm font-medium text-fg">
                  {hasPassword ? 'Change Password (Optional)' : 'Set a Password (Optional)'}
                </h4>
                <p className="mb-4 text-xs text-fg-muted">
                  {hasPassword
                    ? 'Leave blank to keep your current password.'
                    : 'You sign in with Google, so you have no password yet. Adding one gives you a way in if you ever lose access to your Google account.'}
                </p>

                <div className="space-y-4">
                  {hasPassword && (
                    <Input
                      label="Current Password"
                      type="password"
                      {...register('current_password')}
                      error={errors.current_password?.message}
                      fullWidth
                      placeholder="Enter your current password"
                      autoComplete="current-password"
                    />
                  )}

                  <Input
                    label={hasPassword ? 'New Password' : 'Password'}
                    type="password"
                    {...register('new_password')}
                    error={errors.new_password?.message}
                    fullWidth
                    placeholder="Enter a new password"
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div className="border-t border-border pt-6">
                <h4 className="mb-1 text-sm font-medium text-fg">ESPN league access</h4>
                <p className="mb-4 text-xs text-fg-muted">
                  {espnLeagues.length === 0
                    ? 'Nothing to do here unless you connect a private ESPN league. Sleeper needs no credentials at all.'
                    : 'Only private ESPN leagues need this. Paste your full cookie string to fill both fields, or enter them by hand. They are encrypted before they are stored.'}
                </p>

                <div className="space-y-4">
                  <Input
                    label="Paste ESPN Cookies"
                    type="text"
                    {...espnCookiesField}
                    onChange={handlePasteCookies}
                    error={errors.espn_cookies?.message}
                    fullWidth
                    placeholder="Paste the full cookie string (espn_s2=...; SWID=...)"
                  />

                  <Input
                    label="ESPN S2 Cookie"
                    type="text"
                    {...register('espn_s2')}
                    error={errors.espn_s2?.message}
                    fullWidth
                    placeholder="espn_s2 cookie value"
                  />

                  <Input
                    label="ESPN SWID Cookie"
                    type="text"
                    {...register('espn_swid')}
                    error={errors.espn_swid?.message}
                    fullWidth
                    placeholder="SWID cookie value (usually starts with {)"
                  />
                </div>
              </div>

              <Button type="submit" loading={isSubmitting} fullWidth>
                Save Changes
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
};
