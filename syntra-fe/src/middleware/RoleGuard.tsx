import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

type UserRole = 'admin' | 'user';

interface RoleGuardProps {
    children: React.ReactNode;
    allowedRoles: UserRole[];
}

export const RoleGuard: React.FC<RoleGuardProps> = ({ children, allowedRoles }) => {
    const { isAuthenticated, user } = useAuthStore();
    const location = useLocation();

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (!user || !allowedRoles.includes(user.role as UserRole)) {
        const redirectPath = user?.role === 'admin' ? '/admin/dashboard' : '/chat';
        return <Navigate to={redirectPath} replace />;
    }

    return <>{children}</>;
};

export const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return <RoleGuard allowedRoles={['admin']}>{children}</RoleGuard>;
};

export const UserGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return <RoleGuard allowedRoles={['user']}>{children}</RoleGuard>;
};
