import React, { ReactNode } from 'react';

interface ChatLayoutProps {
    sidebar: ReactNode;
    children: ReactNode;
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({ sidebar, children }) => {
    return (
        <div className="font-display h-screen w-full overflow-hidden spotlight-bg flex text-sm antialiased selection:bg-white/90 selection:text-black">
            {sidebar}
            <main className="flex-1 flex flex-col h-full min-w-0 relative z-10">
                {children}
            </main>
        </div>
    );
};
