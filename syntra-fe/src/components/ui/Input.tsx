import React, { forwardRef, useState } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    icon?: string;
    showPasswordToggle?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ icon, showPasswordToggle, type, className = '', ...props }, ref) => {
        const [showPassword, setShowPassword] = useState(false);
        const isPassword = type === 'password';
        const inputType = isPassword && showPassword ? 'text' : type;

        return (
            <div className="group relative">
                <div className="relative flex items-center">
                    {icon && (
                        <span
                            className="material-symbols-outlined absolute left-4 text-white/30 transition-colors group-focus-within:text-white"
                            style={{ fontSize: '20px' }}
                        >
                            {icon}
                        </span>
                    )}
                    <input
                        ref={ref}
                        type={inputType}
                        className={`
                            h-12 w-full rounded-lg border border-white/10 bg-black/40 
                            ${icon ? 'pl-11' : 'pl-4'} 
                            ${isPassword && showPasswordToggle ? 'pr-12' : 'pr-4'} 
                            text-sm text-white placeholder-white/20 
                            transition-all 
                            focus:border-white/40 focus:bg-black/60 focus:outline-none focus:ring-1 focus:ring-white/20
                            ${className}
                        `}
                        {...props}
                    />
                    {isPassword && showPasswordToggle && (
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-4 flex items-center text-white/30 hover:text-white transition-colors"
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
                                {showPassword ? 'visibility_off' : 'visibility'}
                            </span>
                        </button>
                    )}
                </div>
            </div>
        );
    }
);

Input.displayName = 'Input';
