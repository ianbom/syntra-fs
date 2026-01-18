import React from 'react';

interface ChatHeaderProps {
    title?: string;
    isOnline?: boolean;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({ title = "Server Log Analysis", isOnline = true }) => {
    return (
        <header className="flex items-center justify-between px-6 py-4 border-b border-white/10 glass-panel">
            <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-gray-500 text-lg">tag</span>
                <div className="flex flex-col">
                    <h2 className="text-white font-semibold text-base leading-none">{title}</h2>
                    {isOnline && (
                        <div className="flex items-center gap-1.5 mt-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_15px_rgba(255,255,255,0.3)]"></span>
                            <span className="text-gray-300 text-xs font-medium tracking-wide">Online</span>
                        </div>
                    )}
                </div>
            </div>
            <div className="flex items-center gap-2">
                <button className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                    <span className="material-symbols-outlined text-xl">ios_share</span>
                </button>
                <button className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                    <span className="material-symbols-outlined text-xl">history</span>
                </button>
                <button className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                    <span className="material-symbols-outlined text-xl">more_vert</span>
                </button>
            </div>
        </header>
    );
};
