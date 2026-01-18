import apiClient from '../lib/axios';
import type { LoginCredentials, AuthResponse, User } from '../types/auth.types';

interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    user: User;
}

export const AuthService = {
    async login(credentials: LoginCredentials): Promise<AuthResponse> {
        const formData = new FormData();
        formData.append('username', credentials.email);
        formData.append('password', credentials.password);

        const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });

        return {
            user: response.data.user,
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
        };
    },

    async fetchCurrentUser(): Promise<User> {
        const response = await apiClient.get<User>('/auth/me');
        return response.data;
    },

    async refreshToken(refresh_token: string): Promise<AuthResponse> {
        const response = await apiClient.post<LoginResponse>('/auth/refresh', { refresh_token });
        return {
            user: response.data.user,
            accessToken: response.data.access_token,
            refreshToken: response.data.refresh_token,
        };
    }
};
