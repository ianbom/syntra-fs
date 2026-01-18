import React from 'react';
import { Link } from 'react-router-dom';
import { Conversation } from '../../../services/chatService';

interface ChatSidebarProps {
    conversations: Conversation[];
    activeConversationId: number | null;
    onSelectConversation: (id: number) => void;
    onNewChat: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
    conversations,
    activeConversationId,
    onSelectConversation,
    onNewChat
}) => {
    return (
        <aside className="w-[280px] flex-shrink-0 flex flex-col justify-between h-full border-r border-white/10 glass-panel z-20 transition-all duration-300">
            <div className="flex flex-col h-full p-4">
                <div className="flex items-center gap-3 px-2 py-4 mb-6">
                    <div className="relative flex items-center justify-center size-8 rounded-lg bg-gradient-to-br from-gray-800 to-black border border-white/20 shadow-lg">
                        <div className="size-2 rounded-full bg-white shadow-[0_0_15px_rgba(255,255,255,0.3)]"></div>
                    </div>
                    <h1 className="text-white text-lg font-bold tracking-tight">Syntra <span className="text-gray-400 font-light opacity-80">AI</span></h1>
                </div>

                <button
                    onClick={onNewChat}
                    className="group flex items-center justify-center w-full gap-2 px-4 py-3 mb-6 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold transition-all duration-200 hover:shadow-[0_0_8px_rgba(255,255,255,0.15)] hover:border-white/20"
                >
                    <span className="material-symbols-outlined text-lg">add</span>
                    <span>New Chat</span>
                </button>

                <nav className="flex flex-col gap-1 flex-1 overflow-y-auto mb-4">
                    <div className="px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Workspace</div>

                    <Link to="/admin/dashboard" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                        <span className="material-symbols-outlined">dashboard</span>
                        <span className="font-medium">Dashboard</span>
                    </Link>

                    <div className="mt-6 px-3 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Recent Chats</div>

                    <div className="flex flex-col gap-1 overflow-y-auto max-h-[calc(100vh-400px)]">
                        {conversations.length === 0 ? (
                            <div className="px-3 py-4 text-center text-xs text-gray-600 italic">
                                No history yet
                            </div>
                        ) : (
                            conversations.map((conv) => (
                                <button
                                    key={conv.id}
                                    onClick={() => onSelectConversation(conv.id)}
                                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors truncate w-full ${activeConversationId === conv.id
                                            ? 'bg-white/10 border border-white/5 text-white shadow-sm'
                                            : 'text-gray-400 hover:text-white hover:bg-white/5'
                                        }`}
                                >
                                    <span className="material-symbols-outlined text-sm flex-shrink-0">chat_bubble_outline</span>
                                    <span className="font-medium text-xs truncate">{conv.title}</span>
                                </button>
                            ))
                        )}
                    </div>
                </nav>

                <div className="flex flex-col gap-1 mt-auto pt-4 border-t border-white/10">
                    <Link to="/settings" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                        <span className="material-symbols-outlined">settings</span>
                        <span className="font-medium">Settings</span>
                    </Link>

                    <div className="flex items-center gap-3 px-3 py-3 mt-1 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:border-white/20 transition-colors group">
                        <div className="size-8 rounded-full bg-gray-700 flex items-center justify-center text-white text-xs font-bold">
                            ME
                        </div>
                        <div className="flex flex-col">
                            <span className="text-white text-xs font-bold">User</span>
                            <span className="text-gray-500 text-[10px]">Pro Plan</span>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
};
