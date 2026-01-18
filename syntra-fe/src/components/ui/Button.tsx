import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    icon?: string;
    iconPosition?: 'left' | 'right';
    isLoading?: boolean;
    children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
    variant = 'primary',
    icon,
    iconPosition = 'right',
    isLoading = false,
    children,
    className = '',
    disabled,
    ...props
}) => {
    const baseStyles = 'relative flex w-full items-center justify-center gap-2 rounded-lg py-3.5 text-sm font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed';

    const variants: Record<ButtonVariant, string> = {
        primary: `
            overflow-hidden bg-white text-black 
            shadow-[0_0_20px_rgba(255,255,255,0.2)] 
            hover:bg-neutral-100 hover:shadow-[0_0_30px_rgba(255,255,255,0.4)] 
            hover:scale-[1.01] active:scale-[0.99]
        `,
        secondary: `
            border border-white/10 bg-transparent text-white 
            hover:bg-white/5 hover:border-white/30 active:bg-white/10
        `,
        ghost: `
            bg-transparent text-white/70 
            hover:text-white hover:bg-white/5
        `,
    };

    return (
        <button
            className={`${baseStyles} ${variants[variant]} ${className}`}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading ? (
                <span className="material-symbols-outlined animate-spin" style={{ fontSize: '18px' }}>
                    progress_activity
                </span>
            ) : (
                <>
                    {icon && iconPosition === 'left' && (
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
                            {icon}
                        </span>
                    )}
                    <span className="relative z-10">{children}</span>
                    {icon && iconPosition === 'right' && (
                        <span
                            className="material-symbols-outlined relative z-10 transition-transform group-hover:translate-x-1"
                            style={{ fontSize: '18px' }}
                        >
                            {icon}
                        </span>
                    )}
                </>
            )}
            {/* Shimmer effect for primary button */}
            {variant === 'primary' && (
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-black/5 to-transparent group-hover:animate-shimmer" />
            )}
        </button>
    );
};
