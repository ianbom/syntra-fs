import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChatLayout } from '../../features/chat/components/ChatLayout';
import { ChatSidebar } from '../../features/chat/components/ChatSidebar';
import { ChatArea } from '../../features/chat/components/ChatArea';
import { MessageProps } from '../../features/chat/components/MessageItem';
import { ChatService } from '../../services/chatService';

const WELCOME_MESSAGE: MessageProps = {
    role: 'bot',
    content: 'Silahkan bertanya pada Syntra, asisten AI Anda.',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
};

const ChatPage: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [messages, setMessages] = useState<MessageProps[]>([WELCOME_MESSAGE]);

    // Fetch conversations history for sidebar
    const { data: conversations = [] } = useQuery({
        queryKey: ['conversations'],
        queryFn: () => ChatService.getConversations(),
    });

    // Send message mutation
    const sendMessageMutation = useMutation({
        mutationFn: ChatService.sendMessage,
        onSuccess: (data) => {
            // Invalidate conversations to update sidebar
            queryClient.invalidateQueries({ queryKey: ['conversations'] });

            // Redirect to the new conversation detail page
            navigate(`/chat/${data.conversation_id}`);
        },
        onError: (err) => {
            console.error(err);
            const errorMsg: MessageProps = {
                role: 'bot',
                content: "Maaf, terjadi kesalahan saat memproses permintaan Anda.",
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            setMessages(prev => [...prev, errorMsg]);
        }
    });

    const handleSendMessage = (content: string) => {
        const userMessage: MessageProps = {
            role: 'user',
            content,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        setMessages(prev => [...prev, userMessage]);

        sendMessageMutation.mutate({
            message: content,
            conversation_id: undefined // New conversation
        });
    };

    const handleNewChat = () => {
        // Already on new chat page, maybe reset state if needed
        setMessages([WELCOME_MESSAGE]);
    };

    const handleSelectConversation = (id: number) => {
        navigate(`/chat/${id}`);
    };

    return (
        <ChatLayout
            sidebar={
                <ChatSidebar
                    conversations={conversations}
                    activeConversationId={null} // No active conversation initially
                    onSelectConversation={handleSelectConversation}
                    onNewChat={handleNewChat}
                />
            }
        >
            <ChatArea
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={sendMessageMutation.isPending}
            />
        </ChatLayout>
    );
};

export default ChatPage;
