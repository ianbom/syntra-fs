import React, { useState } from 'react';
import { AdminHeader } from '../../../features/admin/components';
import { Button, Input } from '../../../components/ui';

interface User {
    id: string;
    name: string;
    email: string;
    role: 'admin' | 'user';
    status: 'active' | 'inactive';
    createdAt: string;
    lastLogin: string;
}

// Mock data - will be replaced with TanStack Query
const mockUsers: User[] = [
    { id: '1', name: 'John Doe', email: 'john@example.com', role: 'admin', status: 'active', createdAt: '2024-01-01', lastLogin: '2 hours ago' },
    { id: '2', name: 'Jane Smith', email: 'jane@example.com', role: 'user', status: 'active', createdAt: '2024-01-05', lastLogin: '1 day ago' },
    { id: '3', name: 'Bob Wilson', email: 'bob@example.com', role: 'user', status: 'inactive', createdAt: '2024-01-08', lastLogin: '1 week ago' },
    { id: '4', name: 'Alice Brown', email: 'alice@example.com', role: 'user', status: 'active', createdAt: '2024-01-10', lastLogin: '5 hours ago' },
    { id: '5', name: 'Charlie Davis', email: 'charlie@example.com', role: 'admin', status: 'active', createdAt: '2024-01-12', lastLogin: '30 mins ago' },
];

const UsersPage: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState('');
    const [users] = useState<User[]>(mockUsers);

    const filteredUsers = users.filter(user =>
        user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const getRoleBadge = (role: User['role']) => {
        return role === 'admin'
            ? 'bg-white/10 text-white border-white/20'
            : 'bg-white/5 text-white/60 border-white/10';
    };

    const getStatusBadge = (status: User['status']) => {
        return status === 'active'
            ? 'bg-green-500/10 text-green-400 border-green-500/20'
            : 'bg-white/5 text-white/40 border-white/10';
    };

    return (
        <div>
            <AdminHeader
                title="Users"
                subtitle="Manage user accounts and permissions"
                actions={
                    <Button variant="primary" icon="person_add" iconPosition="left">
                        Add User
                    </Button>
                }
            />

            {/* Search & Filters */}
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="w-full sm:w-80">
                    <Input
                        type="text"
                        icon="search"
                        placeholder="Search users..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <div className="flex gap-2">
                    <button className="flex items-center gap-2 rounded-lg border border-white/10 bg-surface-glass px-4 py-2 text-sm text-white/70 hover:bg-white/5 transition-colors">
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>filter_list</span>
                        Filter
                    </button>
                    <button className="flex items-center gap-2 rounded-lg border border-white/10 bg-surface-glass px-4 py-2 text-sm text-white/70 hover:bg-white/5 transition-colors">
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>sort</span>
                        Sort
                    </button>
                </div>
            </div>

            {/* Users Table */}
            <div className="rounded-xl border border-white/10 bg-surface-glass backdrop-blur-xl overflow-hidden">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-white/10 bg-black/20">
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">User</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Role</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Status</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Created</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Last Login</th>
                            <th className="text-right px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredUsers.map((user) => (
                            <tr key={user.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white font-semibold">
                                            {user.name.charAt(0)}
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-white">{user.name}</p>
                                            <p className="text-xs text-white/50">{user.email}</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border capitalize ${getRoleBadge(user.role)}`}>
                                        {user.role}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border capitalize ${getStatusBadge(user.status)}`}>
                                        {user.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-white/70">{user.createdAt}</span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-white/70">{user.lastLogin}</span>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <button className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors">
                                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>visibility</span>
                                        </button>
                                        <button className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors">
                                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>edit</span>
                                        </button>
                                        <button className="p-2 rounded-lg text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-colors">
                                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>delete</span>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {/* Pagination */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
                    <p className="text-sm text-white/50">
                        Showing <span className="text-white">{filteredUsers.length}</span> of <span className="text-white">{users.length}</span> users
                    </p>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 rounded-lg border border-white/10 text-sm text-white/50 hover:bg-white/5 transition-colors disabled:opacity-50" disabled>
                            Previous
                        </button>
                        <button className="px-3 py-1.5 rounded-lg bg-white text-black text-sm font-medium">
                            1
                        </button>
                        <button className="px-3 py-1.5 rounded-lg border border-white/10 text-sm text-white/50 hover:bg-white/5 transition-colors">
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UsersPage;
