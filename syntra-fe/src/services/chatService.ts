import apiClient from '../lib/axios';

export interface ChatReference {
    id: number;
    document_title: string;
    page_number?: number;
    quote: string;
    relevance_score: number;
    file_path?: string;
    document_id: number;
}

export interface ChatResponse {
    id: number;
    conversation_id: number;
    role: 'user' | 'bot';
    message: string;
    created_at: string;
    references?: ChatReference[];
}

export interface Conversation {
    id: number;
    title: string;
    is_pinned: boolean;
    updated_at: string;
}

export interface ConversationDetail extends Conversation {
    chats: ChatResponse[];
}

export interface SendMessageRequest {
    message: string;
    conversation_id?: number;
}

export const ChatService = {
    async sendMessage(data: SendMessageRequest): Promise<ChatResponse> {
        const response = await apiClient.post<ChatResponse>('/chats/', data);
        return response.data;
    },

    async getConversations(limit: number = 20, offset: number = 0): Promise<Conversation[]> {
        const response = await apiClient.get<Conversation[]>('/chats/conversations', {
            params: { limit, offset }
        });
        return response.data;
    },

    async getConversation(id: number): Promise<ConversationDetail> {
        const response = await apiClient.get<ConversationDetail>(`/chats/conversations/${id}`);
        return response.data;
    }
};
