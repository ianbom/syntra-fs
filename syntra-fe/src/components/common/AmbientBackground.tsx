import React from 'react';

interface AmbientBackgroundProps {
    variant?: 'default' | 'auth';
}

export const AmbientBackground: React.FC<AmbientBackgroundProps> = ({ variant = 'default' }) => {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none">
            {/* Grid Pattern */}
            <div className="absolute inset-0 bg-grid-pattern bg-[size:40px_40px] opacity-10" />

            {/* Gradient Mesh / Light Streaks - Monochrome */}
            <div className="absolute top-[-20%] left-[-10%] h-[500px] w-[500px] rounded-full bg-white/5 blur-[120px]" />
            <div className="absolute bottom-[-20%] right-[-10%] h-[600px] w-[600px] rounded-full bg-white/5 blur-[140px]" />

            {/* Center spotlight for card (only on auth variant) */}
            {variant === 'auth' && (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[800px] w-[800px] rounded-full bg-white/[0.01] blur-[80px]" />
            )}
        </div>
    );
};
