import axios from 'axios';

const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Check for 401 Unauthorized or other global errors here
        if (error.response?.status === 401) {
            // Handle unauthorized (e.g., redirect to login)
            console.error('Unauthorized access');
        }
        return Promise.reject(error);
    }
);

export default apiClient;
