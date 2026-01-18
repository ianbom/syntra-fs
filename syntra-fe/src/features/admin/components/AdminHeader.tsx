import React from 'react';

interface AdminHeaderProps {
    title: string;
    subtitle?: string;
    actions?: React.ReactNode;
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({ title, subtitle, actions }) => {
    return (
        <header className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between mb-8">
            <div>
                <h1 className="font-display text-2xl font-bold text-white">{title}</h1>
                {subtitle && (
                    <p className="text-sm text-white/50 mt-1">{subtitle}</p>
                )}
            </div>
            {actions && <div className="mt-4 sm:mt-0">{actions}</div>}
        </header>
    );
};
