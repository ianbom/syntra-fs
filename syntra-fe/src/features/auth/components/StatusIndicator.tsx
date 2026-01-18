import React from 'react';

interface StatusIndicatorProps {
    status?: 'operational' | 'degraded' | 'offline';
    label?: string;
    version?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
    status = 'operational',
    label,
    version,
}) => {
    const statusLabels = {
        operational: 'SYSTEM ONLINE',
        degraded: 'DEGRADED PERFORMANCE',
        offline: 'SYSTEM OFFLINE',
    };

    return (
        <>
            <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse shadow-[0_0_5px_rgba(255,255,255,0.5)]" />
                {label || statusLabels[status]}
            </span>
            {version && <span>V {version}</span>}
        </>
    );
};
