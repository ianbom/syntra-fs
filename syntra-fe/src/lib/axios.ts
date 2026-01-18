import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor
apiClient.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().accessToken;
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Check for 401 Unauthorized or other global errors here
        if (error.response?.status === 401) {
            // Handle unauthorized (e.g., redirect to login)
            console.error('Unauthorized access');
            useAuthStore.getState().logout();
        }
        return Promise.reject(error);
    }
);

export default apiClient;
