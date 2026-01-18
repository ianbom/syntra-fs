import apiClient from '../lib/axios';
import type { Document, UploadDocumentParams } from '../types/document.types';

export const DocumentService = {
    async uploadDocument(params: UploadDocumentParams): Promise<Document> {
        const formData = new FormData();
        formData.append('file', params.file);

        const response = await apiClient.post<Document>('/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            params: {
                type: params.type,
                is_private: params.isPrivate,
            }
        });

        return response.data;
    }
};
