import apiClient from '../lib/axios';
import type { Document, UploadDocumentParams } from '../types/document.types';

export const DocumentService = {
    async uploadDocument(
        params: UploadDocumentParams & { clientId?: string }
    ): Promise<Document> {
        const formData = new FormData();
        formData.append('file', params.file);

        const response = await apiClient.post<Document>('/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            params: {
                type: params.type,
                is_private: params.isPrivate,
                client_id: params.clientId,
            }
        });

        return response.data;
    },

    async deleteDocument(id: number) {
        const response = await apiClient.delete(`/documents/${id}`);
        return response.data;
    },

    async getDownloadUrl(id: number) {
        const response = await apiClient.get<{ download_url: string; filename: string }>(`/documents/${id}/download`);
        return response.data;
    }
};
