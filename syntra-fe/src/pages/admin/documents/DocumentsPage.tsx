import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AdminHeader } from '../../../features/admin/components';
import { Button, Input } from '../../../components/ui';

interface Document {
    id: string;
    name: string;
    type: string;
    size: string;
    uploadedAt: string;
    status: 'processed' | 'processing' | 'failed';
}

// Mock data - will be replaced with TanStack Query
const mockDocuments: Document[] = [
    { id: '1', name: 'Company_Policy_2024.pdf', type: 'PDF', size: '2.4 MB', uploadedAt: '2024-01-15', status: 'processed' },
    { id: '2', name: 'Product_Manual_v3.docx', type: 'DOCX', size: '1.8 MB', uploadedAt: '2024-01-14', status: 'processed' },
    { id: '3', name: 'HR_Guidelines.pdf', type: 'PDF', size: '890 KB', uploadedAt: '2024-01-13', status: 'processing' },
    { id: '4', name: 'Technical_Specs.pdf', type: 'PDF', size: '3.2 MB', uploadedAt: '2024-01-12', status: 'processed' },
    { id: '5', name: 'Training_Material.pptx', type: 'PPTX', size: '5.1 MB', uploadedAt: '2024-01-11', status: 'failed' },
];

const DocumentsPage: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState('');
    const [documents] = useState<Document[]>(mockDocuments);

    const filteredDocuments = documents.filter(doc =>
        doc.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const getStatusBadge = (status: Document['status']) => {
        const styles = {
            processed: 'bg-green-500/10 text-green-400 border-green-500/20',
            processing: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
            failed: 'bg-red-500/10 text-red-400 border-red-500/20',
        };
        return styles[status];
    };

    return (
        <div>
            <AdminHeader
                title="Documents"
                subtitle="Manage your knowledge base documents"
                actions={
                    <Link to="/admin/documents/upload">
                        <Button variant="primary" icon="add" iconPosition="left">
                            Upload Document
                        </Button>
                    </Link>
                }
            />

            {/* Search & Filters */}
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="w-full sm:w-80">
                    <Input
                        type="text"
                        icon="search"
                        placeholder="Search documents..."
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

            {/* Documents Table */}
            <div className="rounded-xl border border-white/10 bg-surface-glass backdrop-blur-xl overflow-hidden">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-white/10 bg-black/20">
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Name</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Type</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Size</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Uploaded</th>
                            <th className="text-left px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Status</th>
                            <th className="text-right px-6 py-4 text-xs font-medium uppercase tracking-wider text-white/50">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredDocuments.map((doc) => (
                            <tr key={doc.id} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined text-white" style={{ fontSize: '20px' }}>
                                            description
                                        </span>
                                        <span className="text-sm text-white">{doc.name}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-white/70">{doc.type}</span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-white/70">{doc.size}</span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-white/70">{doc.uploadedAt}</span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusBadge(doc.status)}`}>
                                        {doc.status}
                                    </span>
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
                        Showing <span className="text-white">{filteredDocuments.length}</span> of <span className="text-white">{documents.length}</span> documents
                    </p>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 rounded-lg border border-white/10 text-sm text-white/50 hover:bg-white/5 transition-colors disabled:opacity-50" disabled>
                            Previous
                        </button>
                        <button className="px-3 py-1.5 rounded-lg bg-white text-black text-sm font-medium">
                            1
                        </button>
                        <button className="px-3 py-1.5 rounded-lg border border-white/10 text-sm text-white/50 hover:bg-white/5 transition-colors">
                            2
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

export default DocumentsPage;
