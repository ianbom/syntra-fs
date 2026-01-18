import React from 'react';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { MessageProps } from './MessageItem';

interface ChatAreaProps {
    messages: MessageProps[];
    onSendMessage: (message: string) => void;
    isLoading?: boolean;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ messages, onSendMessage, isLoading }) => {
    return (
        <>
            <ChatHeader />
            <MessageList messages={messages} />
            <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
        </>
    );
};
