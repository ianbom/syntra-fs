import React from 'react';

interface DividerProps {
    text?: string;
}

export const Divider: React.FC<DividerProps> = ({ text }) => {
    return (
        <div className="flex items-center gap-4 py-2">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/10" />
            {text && (
                <span className="text-[10px] font-medium uppercase tracking-widest text-white/20">
                    {text}
                </span>
            )}
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/10" />
        </div>
    );
};
