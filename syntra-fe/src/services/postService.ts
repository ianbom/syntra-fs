import apiClient from '../lib/axios';

export interface Post {
    userId: number;
    id: number;
    title: string;
    body: string;
}

export const getPosts = async (): Promise<Post[]> => {
    const response = await apiClient.get<Post[]>('/posts');
    return response.data;
};
