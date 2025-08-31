import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LoginForm } from '@/components/auth/LoginForm';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLoginSuccess = () => {
    const from = (location.state as any)?.from?.pathname || '/';
    navigate(from, { replace: true });
  };

  return <LoginForm onSuccess={handleLoginSuccess} />;
};