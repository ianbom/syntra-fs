import React from 'react';

interface AuthHeaderProps {
    icon?: string;
    title: string;
    subtitle?: string;
}

export const AuthHeader: React.FC<AuthHeaderProps> = ({
    icon = 'blur_on',
    title,
    subtitle,
}) => {
    return (
        <div className="mb-10 flex flex-col items-center text-center">
            {/* Logo Icon */}
            <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-white/5 border border-white/20 shadow-[0_0_15px_rgba(255,255,255,0.05)]">
                <span
                    className="material-symbols-outlined text-white"
                    style={{ fontSize: '28px' }}
                >
                    {icon}
                </span>
            </div>

            {/* Title */}
            <h1 className="font-display text-3xl font-bold tracking-tight text-white mb-2">
                {title}
            </h1>

            {/* Subtitle */}
            {subtitle && (
                <p className="text-white/40 text-sm font-light tracking-wide">
                    {subtitle}
                </p>
            )}
        </div>
    );
};
