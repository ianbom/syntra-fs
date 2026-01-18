import React, { useState } from 'react';

interface ChatInputProps {
    onSendMessage: (message: string) => void;
    isLoading?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading = false }) => {
    const [input, setInput] = useState('');

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (input.trim() && !isLoading) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="px-4 pb-6 md:px-8 w-full max-w-4xl mx-auto flex flex-col gap-3">
            <div className="flex justify-center gap-3">
                <button className="text-xs font-medium text-gray-400 hover:text-white transition-colors bg-black/40 border border-white/10 px-4 py-2 rounded-full backdrop-blur-md shadow-lg flex items-center gap-2 hover:border-white/30">
                    <span className="material-symbols-outlined text-sm">summarize</span> Summarize
                </button>
                <button className="text-xs font-medium text-gray-400 hover:text-white transition-colors bg-black/40 border border-white/10 px-4 py-2 rounded-full backdrop-blur-md shadow-lg flex items-center gap-2 hover:border-white/30">
                    <span className="material-symbols-outlined text-sm">rocket_launch</span> Generate Plan
                </button>
                <button className="text-xs font-medium text-gray-400 hover:text-white transition-colors bg-black/40 border border-white/10 px-4 py-2 rounded-full backdrop-blur-md shadow-lg flex items-center gap-2 hover:border-white/30">
                    <span className="material-symbols-outlined text-sm">mail</span> Write Email
                </button>
            </div>

            <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-white/10 to-transparent rounded-full opacity-0 group-hover:opacity-100 transition duration-500 blur"></div>
                <form onSubmit={handleSubmit} className="relative flex items-center gap-2 p-2 pr-2 rounded-full glass-input">
                    <button type="button" className="p-3 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
                        <span className="material-symbols-outlined">add_circle</span>
                    </button>

                    <input
                        className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 text-sm h-full py-3"
                        placeholder="Message Astra AI..."
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                    />

                    <button type="button" className="p-3 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-white/5">
                        <span className="material-symbols-outlined">mic</span>
                    </button>

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className={`flex items-center justify-center p-3 rounded-full bg-white text-black shadow-[0_0_15px_rgba(255,255,255,0.3)] transition-transform ${(!input.trim() || isLoading) ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'}`}
                    >
                        {isLoading ? (
                            <span className="material-symbols-outlined animate-spin">refresh</span>
                        ) : (
                            <span className="material-symbols-outlined font-bold">arrow_upward</span>
                        )}
                    </button>
                </form>
            </div>

            <div className="text-center text-[10px] text-gray-600">
                Astra AI can make mistakes. Consider checking important information.
            </div>
        </div>
    );
};
