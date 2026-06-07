import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Link } from 'react-router-dom';
import { metaService, AppMeta } from '@/services/meta';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

interface LoginFormProps {
  onSuccess?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const { login, isLoading } = useAuth();
  const [meta, setMeta] = useState<AppMeta | null>(null);

  useEffect(() => {
    metaService.getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data);
      onSuccess?.();
    } catch (error) {
      // Error handling is done in the AuthContext
    }
  };

  const handleDemoLogin = async () => {
    if (!meta?.demo_credentials) return;
    try {
      await login(meta.demo_credentials);
      onSuccess?.();
    } catch (error) {
      // Error handling is done in the AuthContext
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center">Sign In</CardTitle>
      </CardHeader>
      <CardContent>
        {meta?.mock_mode && meta.demo_credentials && (
          <div className="mb-5 rounded-lg border border-warning-300 bg-warning-50 p-4 dark:bg-warning-900/20">
            <p className="text-sm font-semibold text-warning-800 dark:text-warning-300">Demo / Mock Mode</p>
            <p className="mt-1 text-xs text-warning-700 dark:text-warning-300/90">
              This instance runs on realistic sample data with no external accounts.
              Use the demo account to explore the Draft Room and Press Box.
            </p>
            <Button
              type="button"
              onClick={handleDemoLogin}
              loading={isLoading}
              fullWidth
              className="mt-3"
            >
              Use demo account
            </Button>
            <p className="mt-2 text-center text-xs text-warning-700 dark:text-warning-300/90">
              {meta.demo_credentials.email} / {meta.demo_credentials.password}
            </p>
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            {...register('email')}
            error={errors.email?.message}
            fullWidth
            placeholder="Enter your email"
            autoComplete="email"
          />
          
          <Input
            label="Password"
            type="password"
            {...register('password')}
            error={errors.password?.message}
            fullWidth
            placeholder="Enter your password"
            autoComplete="current-password"
          />
          
          <Button
            type="submit"
            loading={isLoading}
            fullWidth
            className="mt-6"
          >
            Sign In
          </Button>
          
          <div className="text-center mt-4">
            <span className="text-fg-muted">Don't have an account? </span>
            <Link
              to="/register"
              className="font-medium text-brand hover:underline"
            >
              Sign up
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};