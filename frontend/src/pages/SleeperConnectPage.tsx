import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { SleeperLeagueConnectionRequest } from '@/types';
import api from '@/services/api';
import {
  LinkIcon,
  InformationCircleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const sleeperConnectionSchema = z.object({
  league_id: z.string().min(1, 'League ID is required'),
  sleeper_user_id: z.string().min(1, 'Username or User ID is required'),
});

type SleeperConnectionForm = z.infer<typeof sleeperConnectionSchema>;

export const SleeperConnectPage: React.FC = () => {
  const navigate = useNavigate();
  const [isConnecting, setIsConnecting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SleeperConnectionForm>({
    resolver: zodResolver(sleeperConnectionSchema),
  });

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
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Connect Your Sleeper League
        </h1>
        <p className="text-gray-600">
          Link your Sleeper fantasy football league to unlock AI-powered insights
        </p>
      </div>

      {/* Info Banner */}
      <Card className="mb-6 bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <InformationCircleIcon className="h-6 w-6 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900">
              <p className="font-semibold mb-2">How to find your Sleeper information:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Open Sleeper app or visit sleeper.com</li>
                <li>Go to your league</li>
                <li>League ID is in the URL: sleeper.com/leagues/<strong>[LEAGUE_ID]</strong></li>
                <li>Your username is in your profile (top right)</li>
              </ol>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connection Form */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <LinkIcon className="h-6 w-6 text-primary-600" />
            <CardTitle>League Connection</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* League ID */}
            <div>
              <label htmlFor="league_id" className="block text-sm font-medium text-gray-700 mb-2">
                League ID <span className="text-red-500">*</span>
              </label>
              <Input
                id="league_id"
                {...register('league_id')}
                placeholder="e.g., 123456789"
                error={errors.league_id?.message}
                disabled={isConnecting}
              />
              <p className="mt-1 text-xs text-gray-500">
                Found in your league URL or league settings
              </p>
            </div>

            {/* Sleeper Username/User ID */}
            <div>
              <label htmlFor="sleeper_user_id" className="block text-sm font-medium text-gray-700 mb-2">
                Your Sleeper Username or User ID <span className="text-red-500">*</span>
              </label>
              <Input
                id="sleeper_user_id"
                {...register('sleeper_user_id')}
                placeholder="e.g., YourUsername or user_id"
                error={errors.sleeper_user_id?.message}
                disabled={isConnecting}
              />
              <p className="mt-1 text-xs text-gray-500">
                Your Sleeper username (visible in your profile)
              </p>
            </div>

            {/* Benefits List */}
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-semibold text-gray-900 mb-3">
                What you'll get:
              </p>
              <ul className="space-y-2">
                {[
                  'AI-powered trade analysis and recommendations',
                  'Strategic suggestions to improve your team',
                  'Live roster and matchup tracking',
                  'Performance insights and trends',
                ].map((benefit, index) => (
                  <li key={index} className="flex items-start text-sm text-gray-700">
                    <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
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
        <p className="text-sm text-gray-600">
          No API key required - Sleeper data is public and free! 🎉
        </p>
      </div>
    </div>
  );
};
