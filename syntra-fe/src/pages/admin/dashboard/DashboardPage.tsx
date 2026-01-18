import React from 'react';
import { AdminHeader, StatCard } from '../../../features/admin/components';

const DashboardPage: React.FC = () => {
    // Mock data - will be replaced with TanStack Query
    const stats = [
        { title: 'Total Documents', value: '1,284', icon: 'description', trend: { value: 12, isPositive: true } },
        { title: 'Active Users', value: '423', icon: 'group', trend: { value: 8, isPositive: true } },
        { title: 'Chat Sessions', value: '8,491', icon: 'chat', trend: { value: 23, isPositive: true } },
        { title: 'Storage Used', value: '45.2 GB', icon: 'database', trend: { value: 5, isPositive: false } },
    ];

    return (
        <div>
            <AdminHeader
                title="Dashboard"
                subtitle="Welcome back! Here's an overview of your knowledge base."
            />

            {/* Stats Grid */}
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
                {stats.map((stat, index) => (
                    <StatCard
                        key={index}
                        title={stat.title}
                        value={stat.value}
                        icon={stat.icon}
                        trend={stat.trend}
                    />
                ))}
            </div>

            {/* Recent Activity Section */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* Recent Documents */}
                <div className="rounded-xl border border-white/10 bg-surface-glass backdrop-blur-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-white" style={{ fontSize: '20px' }}>
                            description
                        </span>
                        Recent Documents
                    </h2>
                    <div className="space-y-3">
                        {[
                            { name: 'Company_Policy_2024.pdf', size: '2.4 MB', date: '2 hours ago' },
                            { name: 'Product_Manual_v3.docx', size: '1.8 MB', date: '5 hours ago' },
                            { name: 'HR_Guidelines.pdf', size: '890 KB', date: '1 day ago' },
                            { name: 'Technical_Specs.pdf', size: '3.2 MB', date: '2 days ago' },
                        ].map((doc, index) => (
                            <div key={index} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                <div className="flex items-center gap-3">
                                    <span className="material-symbols-outlined text-white/40" style={{ fontSize: '20px' }}>
                                        article
                                    </span>
                                    <div>
                                        <p className="text-sm text-white">{doc.name}</p>
                                        <p className="text-xs text-white/40">{doc.size}</p>
                                    </div>
                                </div>
                                <span className="text-xs text-white/40">{doc.date}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recent Users */}
                <div className="rounded-xl border border-white/10 bg-surface-glass backdrop-blur-xl p-6">
                    <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-white" style={{ fontSize: '20px' }}>
                            group
                        </span>
                        Recent Users
                    </h2>
                    <div className="space-y-3">
                        {[
                            { name: 'John Doe', email: 'john@example.com', status: 'active' },
                            { name: 'Jane Smith', email: 'jane@example.com', status: 'active' },
                            { name: 'Bob Wilson', email: 'bob@example.com', status: 'inactive' },
                            { name: 'Alice Brown', email: 'alice@example.com', status: 'active' },
                        ].map((user, index) => (
                            <div key={index} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                                <div className="flex items-center gap-3">
                                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white text-sm font-semibold">
                                        {user.name.charAt(0)}
                                    </div>
                                    <div>
                                        <p className="text-sm text-white">{user.name}</p>
                                        <p className="text-xs text-white/40">{user.email}</p>
                                    </div>
                                </div>
                                <span className={`text-xs px-2 py-1 rounded-full ${user.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-white/5 text-white/40'}`}>
                                    {user.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardPage;
