import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { extractESPNCookies } from '@/utils';

const profileSchema = z
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
  .refine((data) => !data.new_password || !!data.current_password, {
    message: 'Current password is required to set a new password',
    path: ['current_password'],
  });

type ProfileFormData = z.infer<typeof profileSchema>;

export const ProfilePage: React.FC = () => {
  const { user, updateProfile } = useAuth();

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
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
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-display-sm text-fg">Profile Settings</h1>
        <p className="mt-2 text-fg-muted">
          Manage your account details and ESPN league credentials.
        </p>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <dt className="text-sm text-fg-muted">Full name</dt>
                <dd className="text-sm font-medium text-fg">
                  {user?.full_name || 'Not set'}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-sm text-fg-muted">Email</dt>
                <dd className="text-sm font-medium text-fg">{user?.email}</dd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <dt className="text-sm text-fg-muted">ESPN credentials</dt>
                <dd>
                  {user?.has_espn_credentials ? (
                    <Badge variant="success" size="sm">
                      Connected
                    </Badge>
                  ) : (
                    <Badge variant="warning" size="sm">
                      Not connected
                    </Badge>
                  )}
                </dd>
              </div>
            </dl>
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
                  Change Password (Optional)
                </h4>
                <p className="mb-4 text-xs text-fg-muted">
                  Leave blank to keep your current password.
                </p>

                <div className="space-y-4">
                  <Input
                    label="Current Password"
                    type="password"
                    {...register('current_password')}
                    error={errors.current_password?.message}
                    fullWidth
                    placeholder="Enter your current password"
                    autoComplete="current-password"
                  />

                  <Input
                    label="New Password"
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
                <h4 className="mb-1 text-sm font-medium text-fg">
                  ESPN League Access (Optional)
                </h4>
                <p className="mb-4 text-xs text-fg-muted">
                  For private leagues, paste your full ESPN cookie string to
                  auto-fill, or enter the values manually. You can find these in
                  your browser cookies when logged into ESPN.
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
    </div>
  );
};
