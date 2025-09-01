import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useConnectLeague } from '@/hooks/useLeagues';
import { LeagueConnectionRequest } from '@/types';
import { 
  LinkIcon, 
  InformationCircleIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const leagueConnectionSchema = z.object({
  league_id: z
    .string()
    .min(1, 'League ID is required')
    .transform((val) => parseInt(val, 10))
    .refine((val) => !isNaN(val) && val > 0, 'League ID must be a valid number'),
  espn_s2: z.string().optional(),
  espn_swid: z.string().optional(),
});

type LeagueConnectionForm = z.infer<typeof leagueConnectionSchema>;

export const LeagueConnectPage: React.FC = () => {
  const navigate = useNavigate();
  const connectLeague = useConnectLeague();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setValue,
  } = useForm<LeagueConnectionForm>({
    resolver: zodResolver(leagueConnectionSchema),
  });

  const watchedLeagueId = watch('league_id');
  const watchedEspnS2 = watch('espn_s2');
  const watchedEspnSwid = watch('espn_swid');

  const extractLeagueIdFromUrl = (url: string) => {
    const match = url.match(/leagueId=(\d+)/);
    if (match) {
      return match[1];
    }
    return '';
  };

  const onSubmit = async (data: LeagueConnectionForm) => {
    try {
      const connectionData: LeagueConnectionRequest = {
        league_id: data.league_id,
      };

      if (data.espn_s2?.trim()) {
        connectionData.espn_s2 = data.espn_s2.trim();
      }

      if (data.espn_swid?.trim()) {
        connectionData.espn_swid = data.espn_swid.trim();
      }

      const result = await connectLeague.mutateAsync(connectionData);
      
      if (result.success) {
        toast.success('League connected successfully!');
        // Small delay to allow React Query cache invalidation to complete
        setTimeout(() => {
          navigate('/dashboard');
        }, 500);
      }
    } catch (error) {
      console.error('Failed to connect league:', error);
    }
  };

  const handleUrlPaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = event.clipboardData.getData('text');
    const extractedId = extractLeagueIdFromUrl(pastedText);
    if (extractedId) {
      setValue('league_id', extractedId as any);
      toast.success('League ID extracted from URL!');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Connect Your ESPN League
        </h1>
        <p className="text-gray-600">
          Connect your ESPN Fantasy Football league to get intelligent insights and analysis.
        </p>
      </div>

      <div className="space-y-6">
        {/* Instructions Card */}
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="text-blue-900 flex items-center">
              <InformationCircleIcon className="h-5 w-5 mr-2" />
              How to Connect Your League
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-blue-800 text-sm space-y-2">
              <p className="font-medium">Option 1: Use League ID (Easiest)</p>
              <ol className="list-decimal list-inside space-y-1 ml-4">
                <li>Go to your ESPN Fantasy Football league</li>
                <li>Copy the League ID from the URL (the number after "leagueId=")</li>
                <li>Paste it below</li>
              </ol>
              <p className="font-medium mt-3">Option 2: Paste Full URL</p>
              <p className="ml-4">Paste your full ESPN league URL and we'll extract the League ID automatically.</p>
            </div>
          </CardContent>
        </Card>

        {/* Connection Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LinkIcon className="h-5 w-5 mr-2" />
              League Connection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <label htmlFor="league_id" className="block text-sm font-medium text-gray-700 mb-2">
                  ESPN League ID or Full URL
                </label>
                <Input
                  id="league_id"
                  type="text"
                  placeholder="Enter League ID (e.g., 1725275280) or paste full URL"
                  {...register('league_id')}
                  onPaste={handleUrlPaste}
                  error={errors.league_id?.message}
                  className="font-mono"
                />
                {watchedLeagueId && (
                  <div className="mt-2 flex items-center text-sm text-green-600">
                    <CheckCircleIcon className="h-4 w-4 mr-1" />
                    League ID: {watchedLeagueId}
                  </div>
                )}
              </div>

              {/* Advanced Options Toggle */}
              <div className="border-t pt-4">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center text-sm text-gray-600 hover:text-gray-900"
                >
                  <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                  {showAdvanced ? 'Hide' : 'Show'} ESPN Credentials (For Private Leagues)
                </button>
              </div>

              {showAdvanced && (
                <div className="space-y-4 p-4 bg-gray-50 rounded-lg border">
                  <div className="text-sm text-gray-600 mb-4">
                    <p className="font-medium text-gray-800 mb-2">ESPN Credentials (Optional)</p>
                    <p>
                      Only needed for private leagues or if you want real-time roster updates. 
                      You can find these in your browser cookies when logged into ESPN.
                    </p>
                  </div>

                  <div>
                    <label htmlFor="espn_s2" className="block text-sm font-medium text-gray-700 mb-2">
                      ESPN S2 Cookie
                    </label>
                    <Input
                      id="espn_s2"
                      type="password"
                      placeholder="espn_s2 cookie value"
                      {...register('espn_s2')}
                      error={errors.espn_s2?.message}
                    />
                  </div>

                  <div>
                    <label htmlFor="espn_swid" className="block text-sm font-medium text-gray-700 mb-2">
                      ESPN SWID Cookie
                    </label>
                    <Input
                      id="espn_swid"
                      type="text"
                      placeholder="SWID cookie value (usually starts with {)"
                      {...register('espn_swid')}
                      error={errors.espn_swid?.message}
                    />
                  </div>

                  {(watchedEspnS2 || watchedEspnSwid) && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                      <div className="flex items-start">
                        <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400 mr-2 mt-0.5" />
                        <div className="text-sm text-yellow-800">
                          <p className="font-medium">Security Note</p>
                          <p>Your ESPN credentials are encrypted and stored securely. They're only used to access your league data.</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex space-x-3">
                <Button
                  type="submit"
                  disabled={isSubmitting || connectLeague.isLoading}
                  className="flex-1"
                >
                  {(isSubmitting || connectLeague.isLoading) ? (
                    <>
                      <LoadingSpinner size="sm" className="mr-2" />
                      Connecting League...
                    </>
                  ) : (
                    'Connect League'
                  )}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => navigate('/dashboard')}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Help Card */}
        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Need Help?</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-gray-600 space-y-2">
              <p>
                <strong>Public Leagues:</strong> Only the League ID is needed. You can find this in your ESPN league URL.
              </p>
              <p>
                <strong>Private Leagues:</strong> You'll need ESPN S2 and SWID cookies. Check our documentation for detailed instructions.
              </p>
              <p>
                <strong>Example URL:</strong>{' '}
                <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
                  https://fantasy.espn.com/football/team?leagueId=1234567&teamId=1
                </code>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};