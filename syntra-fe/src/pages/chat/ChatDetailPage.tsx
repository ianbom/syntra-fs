import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChatLayout } from '../../features/chat/components/ChatLayout';
import { ChatSidebar } from '../../features/chat/components/ChatSidebar';
import { ChatArea } from '../../features/chat/components/ChatArea';
import { MessageProps } from '../../features/chat/components/MessageItem';
import { ChatService } from '../../services/chatService';

const ChatDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const conversationId = Number(id);

    const [messages, setMessages] = useState<MessageProps[]>([]);

    // Fetch conversations list for sidebar
    const { data: conversations = [] } = useQuery({
        queryKey: ['conversations'],
        queryFn: () => ChatService.getConversations(),
    });

    // Fetch active conversation detail
    const { data: conversationDetail, isLoading: isDetailLoading } = useQuery({
        queryKey: ['conversation', conversationId],
        queryFn: () => ChatService.getConversation(conversationId),
        enabled: !!conversationId,
    });

    // Update messages when conversation detail is loaded
    useEffect(() => {
        if (conversationDetail) {
            const historyMessages: MessageProps[] = conversationDetail.chats.map(chat => ({
                role: chat.role,
                content: chat.message,
                timestamp: new Date(chat.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                references: chat.references?.map(ref => ({
                    document_title: ref.document_title,
                    quote: ref.quote,
                    page_number: ref.page_number,
                    file_path: ref.file_path,
                    document_id: ref.document_id
                }))
            }));
            setMessages(historyMessages);
        }
    }, [conversationDetail]);

    // Send message mutation
    const sendMessageMutation = useMutation({
        mutationFn: ChatService.sendMessage,
        onSuccess: (data) => {
            const botResponse: MessageProps = {
                role: data.role,
                content: data.message,
                timestamp: new Date(data.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                references: data.references?.map(ref => ({
                    document_title: ref.document_title,
                    quote: ref.quote,
                    page_number: ref.page_number,
                    file_path: ref.file_path,
                    document_id: ref.document_id
                }))
            };
            setMessages(prev => [...prev, botResponse]);
            // Invalidate conversation detail to ensure sync? Not strictly necessary if we update local state.
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
            conversation_id: conversationId
        });
    };

    const handleNewChat = () => {
        navigate('/chat');
    };

    const handleSelectConversation = (selectedId: number) => {
        navigate(`/chat/${selectedId}`);
    };

    return (
        <ChatLayout
            sidebar={
                <ChatSidebar
                    conversations={conversations}
                    activeConversationId={conversationId}
                    onSelectConversation={handleSelectConversation}
                    onNewChat={handleNewChat}
                />
            }
        >
            <ChatArea
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={sendMessageMutation.isPending || isDetailLoading}
            />
        </ChatLayout>
    );
};

export default ChatDetailPage;
