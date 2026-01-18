import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginPage } from '../pages/auth';
import { DashboardPage, DocumentsPage, UsersPage } from '../pages/admin';
import { UploadDocumentPage } from '../pages/admin/documents';
import ChatPage from '../pages/chat/ChatPage';
import ChatDetailPage from '../pages/chat/ChatDetailPage';
import { AdminLayout } from '../components/layouts';
import { GuestGuard, AdminGuard, AuthGuard } from '../middleware';

export const router = createBrowserRouter([
    // Auth Routes (Guest only)
    {
        path: '/login',
        element: (
            <GuestGuard>
                <LoginPage />
            </GuestGuard>
        ),
    },

    // Admin Routes
    {
        path: '/admin',
        element: (
            <AdminGuard>
                <AdminLayout />
            </AdminGuard>
        ),
        children: [
            {
                index: true,
                element: <Navigate to="/admin/dashboard" replace />,
            },
            {
                path: 'dashboard',
                element: <DashboardPage />,
            },
            {
                path: 'documents',
                element: <DocumentsPage />,
            },
            {
                path: 'documents/upload',
                element: <UploadDocumentPage />,
            },
            {
                path: 'users',
                element: <UsersPage />,
            },
        ],
    },

    // Chat Routes
    {
        path: '/chat',
        element: (
            <AuthGuard>
                <ChatPage />
            </AuthGuard>
        ),
    },
    {
        path: '/chat/:id',
        element: (
            <AuthGuard>
                <ChatDetailPage />
            </AuthGuard>
        ),
    },

    // Default redirect
    {
        path: '/',
        element: <Navigate to="/login" replace />,
    },

    // 404 - Not Found
    {
        path: '*',
        element: (
            <div className="flex min-h-screen items-center justify-center bg-background-dark text-white">
                <div className="text-center">
                    <h1 className="text-6xl font-bold text-white mb-4">404</h1>
                    <p className="text-white/50">Page not found</p>
                </div>
            </div>
        ),
    },
]);
