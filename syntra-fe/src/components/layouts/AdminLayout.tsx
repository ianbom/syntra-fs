import React from 'react';
import { Outlet } from 'react-router-dom';
import { AdminSidebar } from '../../features/admin/components';
import { AmbientBackground } from '../common';

export const AdminLayout: React.FC = () => {
    return (
        <div className="relative min-h-screen w-full bg-background-dark text-white">
            {/* Ambient Background */}
            <AmbientBackground variant="default" />

            {/* Sidebar */}
            <AdminSidebar />

            {/* Main Content */}
            <main className="relative z-10 ml-64 min-h-screen p-8 transition-all duration-300">
                <Outlet />
            </main>
        </div>
    );
};
