import React from 'react';

interface StatCardProps {
    title: string;
    value: string | number;
    icon: string;
    trend?: {
        value: number;
        isPositive: boolean;
    };
    className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    trend,
    className = '',
}) => {
    return (
        <div
            className={`
                rounded-xl border border-white/10 bg-surface-glass backdrop-blur-xl p-6
                transition-all duration-300 hover:border-white/20 hover:bg-white/[0.04]
                ${className}
            `}
        >
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-sm text-white/50 mb-1">{title}</p>
                    <p className="text-3xl font-bold text-white font-display">{value}</p>
                    {trend && (
                        <div className={`flex items-center gap-1 mt-2 text-xs ${trend.isPositive ? 'text-green-400' : 'text-red-400'}`}>
                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>
                                {trend.isPositive ? 'trending_up' : 'trending_down'}
                            </span>
                            <span>{trend.isPositive ? '+' : ''}{trend.value}% from last month</span>
                        </div>
                    )}
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                    <span className="material-symbols-outlined text-primary" style={{ fontSize: '24px' }}>
                        {icon}
                    </span>
                </div>
            </div>
        </div>
    );
};
