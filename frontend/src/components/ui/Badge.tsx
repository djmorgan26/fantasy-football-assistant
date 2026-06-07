import React from 'react';
import { cn } from '@/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'default',
  size = 'md',
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-full transition-colors';
  
  const variants = {
    default: 'bg-surface-sunken text-fg-muted',
    secondary: 'bg-border text-fg',
    success: 'bg-success-100 text-success-800 dark:bg-success-900/40 dark:text-success-300',
    warning: 'bg-warning-100 text-warning-800 dark:bg-warning-900/40 dark:text-warning-300',
    error: 'bg-error-100 text-error-800 dark:bg-error-900/40 dark:text-error-300',
  };
  
  const sizes = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };
  
  return (
    <span
      className={cn(
        baseClasses,
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};