import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../../store/authStore';

interface NavItem {
    label: string;
    icon: string;
    path: string;
}

const navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', path: '/admin/dashboard' },
    { label: 'Documents', icon: 'description', path: '/admin/documents' },
    { label: 'Users', icon: 'group', path: '/admin/users' },
];

export const AdminSidebar: React.FC = () => {
    const location = useLocation();
    const { user, logout } = useAuthStore();
    const [isCollapsed, setIsCollapsed] = useState(false);

    const isActive = (path: string) => location.pathname === path;

    return (
        <aside
            className={`
                fixed left-0 top-0 z-40 h-screen 
                ${isCollapsed ? 'w-20' : 'w-64'} 
                border-r border-white/10 bg-surface-glass backdrop-blur-2xl
                transition-all duration-300
            `}
        >
            <div className="flex h-full flex-col">
                {/* Logo Header */}
                <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
                    {!isCollapsed && (
                        <div className="flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-primary/20 to-transparent border border-white/10">
                                <span className="material-symbols-outlined text-primary" style={{ fontSize: '20px' }}>
                                    blur_on
                                </span>
                            </div>
                            <span className="font-display text-lg font-bold text-white">Syntra</span>
                        </div>
                    )}
                    <button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-white/50 hover:bg-white/5 hover:text-white transition-colors"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
                            {isCollapsed ? 'chevron_right' : 'chevron_left'}
                        </span>
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 overflow-y-auto p-3">
                    <ul className="space-y-1">
                        {navItems.map((item) => (
                            <li key={item.path}>
                                <Link
                                    to={item.path}
                                    className={`
                                        flex items-center gap-3 rounded-lg px-3 py-2.5 
                                        transition-all duration-200
                                        ${isActive(item.path)
                                            ? 'bg-primary/10 text-primary border border-primary/20'
                                            : 'text-white/60 hover:bg-white/5 hover:text-white border border-transparent'
                                        }
                                    `}
                                >
                                    <span
                                        className="material-symbols-outlined"
                                        style={{ fontSize: '22px' }}
                                    >
                                        {item.icon}
                                    </span>
                                    {!isCollapsed && (
                                        <span className="text-sm font-medium">{item.label}</span>
                                    )}
                                </Link>
                            </li>
                        ))}
                    </ul>
                </nav>

                {/* User Profile & Logout */}
                <div className="border-t border-white/10 p-3">
                    {/* User Info */}
                    <div className={`flex items-center gap-3 rounded-lg px-3 py-2 mb-2 ${isCollapsed ? 'justify-center' : ''}`}>
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-primary font-semibold text-sm">
                            {user?.name?.charAt(0).toUpperCase() || 'A'}
                        </div>
                        {!isCollapsed && (
                            <div className="flex-1 overflow-hidden">
                                <p className="text-sm font-medium text-white truncate">
                                    {user?.name || 'Admin User'}
                                </p>
                                <p className="text-xs text-white/40 truncate">
                                    {user?.email || 'admin@syntra.ai'}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Logout Button */}
                    <button
                        onClick={logout}
                        className={`
                            flex w-full items-center gap-3 rounded-lg px-3 py-2.5 
                            text-white/60 hover:bg-red-500/10 hover:text-red-400 
                            transition-all duration-200 border border-transparent hover:border-red-500/20
                            ${isCollapsed ? 'justify-center' : ''}
                        `}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '22px' }}>
                            logout
                        </span>
                        {!isCollapsed && <span className="text-sm font-medium">Logout</span>}
                    </button>
                </div>
            </div>
        </aside>
    );
};
