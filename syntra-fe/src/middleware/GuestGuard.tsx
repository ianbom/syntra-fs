import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface GuestGuardProps {
    children: React.ReactNode;
}

/**
 * Protects routes that should only be accessible to guests (non-authenticated users).
 * Redirects to appropriate dashboard if user is already authenticated.
 */
export const GuestGuard: React.FC<GuestGuardProps> = ({ children }) => {
    const { isAuthenticated, user } = useAuthStore();

    if (isAuthenticated) {
        // Redirect based on user role
        const redirectPath = user?.role === 'admin' ? '/admin/dashboard' : '/chat';
        return <Navigate to={redirectPath} replace />;
    }

    return <>{children}</>;
};
