import React, { forwardRef } from 'react';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
    ({ label, className = '', ...props }, ref) => {
        return (
            <label className="flex cursor-pointer items-center gap-2 select-none">
                <input
                    ref={ref}
                    type="checkbox"
                    className={`
                        custom-checkbox h-4 w-4 rounded border-white/20 bg-black/40 
                        text-white focus:ring-offset-0 focus:ring-1 focus:ring-white/30 
                        checked:bg-white checked:border-white 
                        transition-colors cursor-pointer
                        ${className}
                    `}
                    {...props}
                />
                {label && (
                    <span className="text-white/60 hover:text-white transition-colors text-xs font-medium">
                        {label}
                    </span>
                )}
            </label>
        );
    }
);

Checkbox.displayName = 'Checkbox';
