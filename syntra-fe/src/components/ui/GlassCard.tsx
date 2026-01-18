import React from 'react';

interface GlassCardProps {
    children: React.ReactNode;
    className?: string;
    animate?: boolean;
    footer?: React.ReactNode;
}

export const GlassCard: React.FC<GlassCardProps> = ({
    children,
    className = '',
    animate = true,
    footer,
}) => {
    return (
        <div
            className={`
                ${animate ? 'animate-fade-in' : ''} 
                w-full max-w-[440px] overflow-hidden rounded-2xl 
                border border-white/10 bg-surface-glass backdrop-blur-2xl 
                shadow-[0_0_50px_-10px_rgba(0,0,0,0.8)]
                ${className}
            `}
        >
            <div className="p-8 sm:p-10">{children}</div>
            {footer && (
                <div className="bg-white/[0.02] border-t border-white/5 px-8 py-3 flex justify-between items-center text-[10px] text-white/30 tracking-wider font-mono">
                    {footer}
                </div>
            )}
        </div>
    );
};
