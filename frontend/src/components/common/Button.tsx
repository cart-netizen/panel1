import React, { forwardRef } from 'react';
import { cn } from '../../utils';
import { LoadingSpinner } from './LoadingScreen';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  className,
  disabled,
  ...props
}, ref) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantClasses = {
    primary: 'bg-primary-600 hover:bg-primary-700 text-white focus:ring-primary-500 shadow-sm hover:shadow-md',
    secondary: 'bg-gray-100 hover:bg-gray-200 text-gray-900 focus:ring-gray-500 border border-gray-300',
    success: 'bg-success-600 hover:bg-success-700 text-white focus:ring-success-500 shadow-sm hover:shadow-md',
    danger: 'bg-danger-600 hover:bg-danger-700 text-white focus:ring-danger-500 shadow-sm hover:shadow-md',
    warning: 'bg-warning-600 hover:bg-warning-700 text-white focus:ring-warning-500 shadow-sm hover:shadow-md',
    ghost: 'bg-transparent hover:bg-gray-100 text-gray-700 hover:text-gray-900 focus:ring-gray-500',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const isDisabled = disabled || loading;

  return (
    <button
      ref={ref}
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        fullWidth && 'w-full',
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {/* Индикатор загрузки */}
      {loading && (
        <LoadingSpinner
          size="sm"
          className="mr-2"
        />
      )}

      {/* Иконка слева */}
      {icon && iconPosition === 'left' && !loading && (
        <span className={cn('flex-shrink-0', children && 'mr-2')}>
          {icon}
        </span>
      )}

      {/* Текст */}
      {children && (
        <span className={loading ? 'opacity-75' : ''}>
          {children}
        </span>
      )}

      {/* Иконка справа */}
      {icon && iconPosition === 'right' && !loading && (
        <span className={cn('flex-shrink-0', children && 'ml-2')}>
          {icon}
        </span>
      )}
    </button>
  );
});

Button.displayName = 'Button';

// Предустановленные варианты кнопок
export const PrimaryButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, 'variant'>>(
  (props, ref) => <Button ref={ref} variant="primary" {...props} />
);

export const SecondaryButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, 'variant'>>(
  (props, ref) => <Button ref={ref} variant="secondary" {...props} />
);

export const SuccessButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, 'variant'>>(
  (props, ref) => <Button ref={ref} variant="success" {...props} />
);

export const DangerButton = forwardRef<HTMLButtonElement, Omit<ButtonProps, 'variant'>>(
  (props, ref) => <Button ref={ref} variant="danger" {...props} />
);

PrimaryButton.displayName = 'PrimaryButton';
SecondaryButton.displayName = 'SecondaryButton';
SuccessButton.displayName = 'SuccessButton';
DangerButton.displayName = 'DangerButton';