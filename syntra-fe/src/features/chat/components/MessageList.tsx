import React, { useRef, useEffect } from 'react';
import { MessageItem, MessageProps } from './MessageItem';

interface MessageListProps {
    messages: MessageProps[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth">
            {messages.map((msg, index) => (
                <MessageItem key={index} {...msg} />
            ))}
            <div ref={bottomRef} className="h-4" />
        </div>
    );
};
