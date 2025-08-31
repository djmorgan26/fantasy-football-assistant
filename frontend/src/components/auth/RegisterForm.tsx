import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Link } from 'react-router-dom';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
  full_name: z.string().optional(),
  espn_s2: z.string().optional(),
  espn_swid: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type RegisterFormData = z.infer<typeof registerSchema>;

interface RegisterFormProps {
  onSuccess?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const { register: registerUser, isLoading } = useAuth();
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      const { confirmPassword, ...registrationData } = data;
      await registerUser(registrationData);
      onSuccess?.();
    } catch (error) {
      // Error handling is done in the AuthContext
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center">Create Account</CardTitle>
      </CardHeader>
      <CardContent>
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
            label="Full Name (Optional)"
            type="text"
            {...register('full_name')}
            error={errors.full_name?.message}
            fullWidth
            placeholder="Enter your full name"
            autoComplete="name"
          />
          
          <Input
            label="Password"
            type="password"
            {...register('password')}
            error={errors.password?.message}
            fullWidth
            placeholder="Enter your password"
            autoComplete="new-password"
          />
          
          <Input
            label="Confirm Password"
            type="password"
            {...register('confirmPassword')}
            error={errors.confirmPassword?.message}
            fullWidth
            placeholder="Confirm your password"
            autoComplete="new-password"
          />
          
          <div className="border-t border-gray-200 pt-4 mt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              ESPN League Access (Optional)
            </h4>
            <p className="text-xs text-gray-600 mb-4">
              For private leagues, you can add your ESPN cookies now or later in your profile.
            </p>
            
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
              placeholder="SWID cookie value"
            />
          </div>
          
          <Button
            type="submit"
            loading={isLoading}
            fullWidth
            className="mt-6"
          >
            Create Account
          </Button>
          
          <div className="text-center mt-4">
            <span className="text-gray-600">Already have an account? </span>
            <Link
              to="/login"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Sign in
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};