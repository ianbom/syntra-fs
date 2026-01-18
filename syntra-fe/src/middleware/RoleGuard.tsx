import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

type UserRole = 'admin' | 'user';

interface RoleGuardProps {
    children: React.ReactNode;
    allowedRoles: UserRole[];
}

/**
 * Protects routes based on user role.
 * Redirects to appropriate page if user doesn't have required role.
 */
export const RoleGuard: React.FC<RoleGuardProps> = ({ children, allowedRoles }) => {
    const { isAuthenticated, user } = useAuthStore();
    const location = useLocation();

    // First check if authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Check if user has required role
    if (!user || !allowedRoles.includes(user.role as UserRole)) {
        // Redirect to appropriate dashboard based on role
        const redirectPath = user?.role === 'admin' ? '/admin/dashboard' : '/chat';
        return <Navigate to={redirectPath} replace />;
    }

    return <>{children}</>;
};

/**
 * Shorthand for admin-only routes
 */
export const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return <RoleGuard allowedRoles={['admin']}>{children}</RoleGuard>;
};

/**
 * Shorthand for user-only routes
 */
export const UserGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return <RoleGuard allowedRoles={['user']}>{children}</RoleGuard>;
};
